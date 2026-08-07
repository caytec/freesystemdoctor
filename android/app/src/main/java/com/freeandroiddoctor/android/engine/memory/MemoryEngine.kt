package com.freeandroiddoctor.android.engine.memory

import android.app.ActivityManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class MemoryInfo(
    val totalBytes: Long,
    val availableBytes: Long,
    val lowMemory: Boolean,
) {
    val usedBytes: Long get() = (totalBytes - availableBytes).coerceAtLeast(0)
    val usedFraction: Float
        get() = if (totalBytes <= 0) 0f else (usedBytes.toFloat() / totalBytes).coerceIn(0f, 1f)
}

/**
 * Reports real RAM usage. We intentionally do NOT ship a "RAM booster": on modern
 * Android killing background processes is ineffective (the system re-spawns them and
 * apps reload), so we only surface honest numbers.
 */
class MemoryEngine(private val context: Context) {

    fun read(): MemoryInfo {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val info = ActivityManager.MemoryInfo()
        am.getMemoryInfo(info)
        return MemoryInfo(
            totalBytes = info.totalMem,
            availableBytes = info.availMem,
            lowMemory = info.lowMemory,
        )
    }

    /**
     * True when the platform still lets us ask for other apps' background processes to
     * be dropped. Since Android 14 (API 34) `killBackgroundProcesses` silently ignores
     * any package other than our own, so on those devices the whole operation is a
     * no-op and we must not pretend otherwise.
     */
    val canReclaimOtherApps: Boolean
        get() = Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE

    /**
     * Result of a reclaim attempt. [supported] = false means the platform refuses the
     * operation entirely, so [freedBytes] is meaningless rather than merely small.
     */
    data class ReclaimResult(val supported: Boolean, val freedBytes: Long)

    /**
     * Asks the system to drop cached background processes for third-party apps.
     *
     * Honest notes:
     *  - On Android 14+ this is impossible: the platform restricts
     *    `killBackgroundProcesses` to the caller's own processes, and AOSP states
     *    plainly that a third-party app cannot improve another app's memory, power or
     *    thermal behaviour. We return [ReclaimResult.supported] = false instead of
     *    reporting a meaningless delta.
     *  - Even below 14 the OS re-spawns and re-caches apps within seconds, and cached
     *    apps are frozen at zero CPU anyway, so any gain is small and temporary. We
     *    report the measured delta, never an inflated "boosted" number.
     */
    suspend fun freeBackground(): ReclaimResult = withContext(Dispatchers.IO) {
        if (!canReclaimOtherApps) return@withContext ReclaimResult(supported = false, freedBytes = 0L)

        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val before = read().availableBytes
        runCatching {
            context.packageManager.getInstalledApplications(0)
                .asSequence()
                .filter { (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 }
                .filter { it.packageName != context.packageName }
                .forEach { am.killBackgroundProcesses(it.packageName) }
        }
        ReclaimResult(
            supported = true,
            freedBytes = (read().availableBytes - before).coerceAtLeast(0),
        )
    }
}
