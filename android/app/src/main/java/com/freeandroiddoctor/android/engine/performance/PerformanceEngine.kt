package com.freeandroiddoctor.android.engine.performance

import android.content.Context
import android.os.Build
import android.os.PowerManager
import android.os.SystemClock
import android.os.storage.StorageManager
import com.freeandroiddoctor.android.engine.battery.BatteryFreedomEngine
import com.freeandroiddoctor.android.engine.memory.MemoryEngine
import com.freeandroiddoctor.android.engine.network.DataUsageEngine
import com.freeandroiddoctor.android.engine.storage.StorageAnalyzerEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.UUID
import java.util.concurrent.TimeUnit

/** One concrete, evidence-backed reason the device is slower than it could be. */
data class Bottleneck(
    val kind: Kind,
    val severity: Severity,
    /** Number the UI formats into the message (percent, count, hours…). */
    val detail: Int = 0,
) {
    enum class Kind {
        THERMAL_THROTTLING,
        STORAGE_CRITICAL,
        STORAGE_LOW,
        BATTERY_EXEMPTIONS,
        LOW_DEEP_SLEEP,
        BACKGROUND_TALKERS,
        MEMORY_PRESSURE,
        LONG_UPTIME,
    }

    enum class Severity { INFO, WARN, CRITICAL }
}

data class PerformanceReport(
    val bottlenecks: List<Bottleneck>,
    /** null when the platform predates API 30 or refuses to answer. */
    val thermalHeadroom: Float?,
    val freeStoragePercent: Int,
    val reclaimableCacheBytes: Long,
) {
    val healthy: Boolean get() = bottlenecks.none { it.severity != Bottleneck.Severity.INFO }
}

/**
 * Finds what is *actually* slowing the device down, and only that.
 *
 * Deliberately absent: any "boost" that kills processes. Since Android 14 that is a no-op
 * for other apps, cached apps are frozen at zero CPU anyway, and AOSP states plainly that
 * a third-party app cannot improve another app's memory, power or thermal behaviour. What
 * *is* real, and what this engine reports:
 *
 *  - thermal throttling (the honest explanation for sudden slowness)
 *  - storage pressure (f2fs enters boosted GC when nearly full; UFS WriteBooster loses its
 *    SLC cache, so write throughput genuinely collapses)
 *  - apps exempted from battery optimisation, poor deep sleep, background network talkers
 *  - memory pressure as reported by the system, not as a made-up percentage
 *  - very long uptime, where a reboot is occasionally the actual fix
 */
class PerformanceEngine(
    private val context: Context,
    private val storage: StorageAnalyzerEngine,
    private val memory: MemoryEngine,
    private val freedom: BatteryFreedomEngine,
    private val dataUsage: DataUsageEngine,
) {

    suspend fun analyze(): PerformanceReport = withContext(Dispatchers.IO) {
        val bottlenecks = ArrayList<Bottleneck>()

        val headroom = thermalHeadroom()
        if (headroom != null && headroom >= THERMAL_WARN) {
            bottlenecks += Bottleneck(
                kind = Bottleneck.Kind.THERMAL_THROTTLING,
                severity = if (headroom >= 1f) Bottleneck.Severity.CRITICAL else Bottleneck.Severity.WARN,
                detail = (headroom * 100).toInt(),
            )
        }

        val volume = runCatching { storage.readPrimaryVolume() }.getOrNull()
        val freePercent = volume?.let {
            if (it.totalBytes <= 0) 100 else ((it.freeBytes * 100) / it.totalBytes).toInt()
        } ?: 100
        when {
            freePercent < STORAGE_CRITICAL_PCT -> bottlenecks += Bottleneck(
                Bottleneck.Kind.STORAGE_CRITICAL, Bottleneck.Severity.CRITICAL, freePercent,
            )
            freePercent < STORAGE_LOW_PCT -> bottlenecks += Bottleneck(
                Bottleneck.Kind.STORAGE_LOW, Bottleneck.Severity.WARN, freePercent,
            )
        }

        val freedomReport = runCatching { freedom.scan() }.getOrNull()
        freedomReport?.let { report ->
            if (report.unrestricted.isNotEmpty()) {
                bottlenecks += Bottleneck(
                    kind = Bottleneck.Kind.BATTERY_EXEMPTIONS,
                    severity = if (report.unrestricted.size >= 5) {
                        Bottleneck.Severity.WARN
                    } else {
                        Bottleneck.Severity.INFO
                    },
                    detail = report.unrestricted.size,
                )
            }
            val awakePct = (report.awakeFraction * 100).toInt()
            if (awakePct > AWAKE_WARN_PCT) {
                bottlenecks += Bottleneck(
                    Bottleneck.Kind.LOW_DEEP_SLEEP, Bottleneck.Severity.WARN, awakePct,
                )
            }
        }

        val talkers = runCatching { dataUsage.backgroundActivity() }.getOrDefault(emptyList())
        if (talkers.isNotEmpty()) {
            bottlenecks += Bottleneck(
                kind = Bottleneck.Kind.BACKGROUND_TALKERS,
                severity = if (talkers.size >= 5) Bottleneck.Severity.WARN else Bottleneck.Severity.INFO,
                detail = talkers.size,
            )
        }

        if (runCatching { memory.read().lowMemory }.getOrDefault(false)) {
            bottlenecks += Bottleneck(
                Bottleneck.Kind.MEMORY_PRESSURE, Bottleneck.Severity.WARN,
            )
        }

        val uptimeDays = TimeUnit.MILLISECONDS.toDays(SystemClock.elapsedRealtime()).toInt()
        if (uptimeDays >= UPTIME_WARN_DAYS) {
            bottlenecks += Bottleneck(
                Bottleneck.Kind.LONG_UPTIME, Bottleneck.Severity.INFO, uptimeDays,
            )
        }

        PerformanceReport(
            bottlenecks = bottlenecks.sortedByDescending { it.severity.ordinal },
            thermalHeadroom = headroom,
            freeStoragePercent = freePercent,
            reclaimableCacheBytes = reclaimableCache(),
        )
    }

    /**
     * 1.0 means the device is at its throttling threshold; above that it is already being
     * throttled. Rate-limited by the platform and NaN shortly after boot, so we normalise
     * anything unusable to null rather than showing a bogus number.
     */
    private fun thermalHeadroom(): Float? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return null
        val power = context.getSystemService(Context.POWER_SERVICE) as? PowerManager ?: return null
        val value = runCatching { power.getThermalHeadroom(0) }.getOrNull() ?: return null
        return if (value.isNaN() || value.isInfinite()) null else value
    }

    /**
     * How many bytes the system would reclaim from *other apps'* caches if we asked for
     * space. This is the only route to cross-app cache clearing without Shizuku.
     */
    private fun reclaimableCache(): Long {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return 0L
        val sm = context.getSystemService(Context.STORAGE_SERVICE) as? StorageManager ?: return 0L
        return runCatching {
            val uuid = storageUuid(sm)
            val allocatable = sm.getAllocatableBytes(uuid)
            val free = context.filesDir.usableSpace
            (allocatable - free).coerceAtLeast(0L)
        }.getOrDefault(0L)
    }

    /**
     * Asks the platform to free [bytes] of space, which makes it delete clearable caches
     * belonging to other apps. Returns the number of bytes that actually became free.
     *
     * This is a slow binder call — IO only, and not more than roughly once per 30 s.
     * It reclaims *storage*, not speed: caches exist to avoid work, so the next launch of
     * a trimmed app is slower. The UI must say so.
     */
    suspend fun reclaimCache(): Long = withContext(Dispatchers.IO) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return@withContext 0L
        val sm = context.getSystemService(Context.STORAGE_SERVICE) as? StorageManager
            ?: return@withContext 0L
        runCatching {
            val uuid = storageUuid(sm)
            val before = context.filesDir.usableSpace
            val target = sm.getAllocatableBytes(uuid)
            if (target > 0) sm.allocateBytes(uuid, target)
            (context.filesDir.usableSpace - before).coerceAtLeast(0L)
        }.getOrDefault(0L)
    }

    private fun storageUuid(sm: StorageManager): UUID =
        runCatching { sm.getUuidForPath(context.filesDir) }
            .getOrDefault(StorageManager.UUID_DEFAULT)

    private companion object {
        /** Headroom at/above this fraction of the throttling threshold is worth reporting. */
        const val THERMAL_WARN = 0.85f
        const val STORAGE_LOW_PCT = 15
        const val STORAGE_CRITICAL_PCT = 10
        const val AWAKE_WARN_PCT = 60
        const val UPTIME_WARN_DAYS = 14
    }
}
