package com.freeandroiddoctor.android.engine.performance

import android.content.Context
import android.os.SystemClock
import com.freeandroiddoctor.android.engine.apps.AppInsightsEngine
import com.freeandroiddoctor.android.engine.network.DataUsageEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.util.concurrent.TimeUnit

/** A daily reading of how well the device is behaving. */
@Serializable
data class HealthSnapshot(
    val timestamp: Long,
    /** Share of time since boot the CPU stayed awake (0..1); higher is worse. */
    val awakeFraction: Float,
    /** Total bytes apps sent in the background over the sampling window. */
    val backgroundBytes: Long,
)

@Serializable
private data class HealthFile(val snapshots: List<HealthSnapshot> = emptyList())

/** An app install/update that lines up in time with the device getting worse. */
data class Regression(
    val packageName: String,
    val label: String,
    val eventAt: Long,
    val wasInstall: Boolean,
    /** Percentage points the awake share moved (positive = worse). */
    val awakeDeltaPoints: Int,
    /** Bytes/day of background traffic added (positive = worse). */
    val backgroundDeltaBytes: Long,
)

data class RegressionReport(
    val regressions: List<Regression>,
    val snapshotCount: Int,
    val state: State,
) {
    enum class State { GATHERING, READY }
}

/**
 * "What made my phone slower?" — lines up app installs and updates against the device's
 * own health history and reports which ones coincide with a measurable regression.
 *
 * Nothing else on the market does this, because nobody else keeps these series together:
 * install events, awake/deep-sleep share and background network volume. Everything is
 * sampled locally once a day and stored in a small JSON file.
 *
 * IMPORTANT: this is *correlation*, not proof. An app that happens to be installed on a
 * bad day will show up. The UI says so explicitly rather than accusing an app.
 */
class RegressionDetectiveEngine(
    context: Context,
    private val insights: AppInsightsEngine,
    private val dataUsage: DataUsageEngine,
) {

    private val dir = File(context.filesDir, "regression").apply { mkdirs() }
    private val file = File(dir, "health.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()

    /** Records one health reading per day. Cheap — safe to call from the daily worker. */
    suspend fun recordToday() = withContext(Dispatchers.IO) {
        val now = System.currentTimeMillis()
        mutex.withLock {
            val current = read().snapshots
            val last = current.lastOrNull()
            if (last != null && now - last.timestamp < TimeUnit.HOURS.toMillis(20)) return@withLock

            val elapsed = SystemClock.elapsedRealtime()
            val awake = SystemClock.uptimeMillis()
            val awakeFraction =
                if (elapsed <= 0) 0f else (awake.toFloat() / elapsed).coerceIn(0f, 1f)
            val background = runCatching { dataUsage.backgroundActivity() }
                .getOrDefault(emptyList())
                .sumOf { it.backgroundBytes }

            val pruned = (current + HealthSnapshot(now, awakeFraction, background))
                .takeLast(MAX_SNAPSHOTS)
            write(HealthFile(pruned))
        }
    }

    /**
     * Correlates recent install/update events with a change in device health. Requires at
     * least [MIN_SNAPSHOTS] readings and at least one on each side of an event.
     */
    suspend fun analyze(): RegressionReport = withContext(Dispatchers.IO) {
        val snapshots = mutex.withLock { read().snapshots }
        if (snapshots.size < MIN_SNAPSHOTS) {
            return@withContext RegressionReport(
                emptyList(), snapshots.size, RegressionReport.State.GATHERING,
            )
        }

        val events = runCatching { insights.report().recentlyInstalled }
            .getOrDefault(emptyList())

        val regressions = events.mapNotNull { event ->
            val before = snapshots.filter { it.timestamp < event.timestamp }
            val after = snapshots.filter { it.timestamp >= event.timestamp }
            if (before.isEmpty() || after.isEmpty()) return@mapNotNull null

            val awakeBefore = before.map { it.awakeFraction }.average()
            val awakeAfter = after.map { it.awakeFraction }.average()
            val awakePoints = ((awakeAfter - awakeBefore) * 100).toInt()

            val bgBefore = before.map { it.backgroundBytes }.average()
            val bgAfter = after.map { it.backgroundBytes }.average()
            val bgDelta = (bgAfter - bgBefore).toLong()

            // Only report changes big enough to be worth a user's attention.
            val worseAwake = awakePoints >= AWAKE_POINTS_THRESHOLD
            val worseBackground = bgDelta >= BACKGROUND_BYTES_THRESHOLD
            if (!worseAwake && !worseBackground) return@mapNotNull null

            Regression(
                packageName = event.packageName,
                label = event.label,
                eventAt = event.timestamp,
                wasInstall = event.isInstall,
                awakeDeltaPoints = awakePoints,
                backgroundDeltaBytes = bgDelta,
            )
        }.sortedByDescending { it.awakeDeltaPoints }

        RegressionReport(regressions, snapshots.size, RegressionReport.State.READY)
    }

    private fun read(): HealthFile =
        if (!file.exists()) HealthFile()
        else runCatching { json.decodeFromString<HealthFile>(file.readText()) }
            .getOrElse { HealthFile() }

    private fun write(data: HealthFile) {
        runCatching { file.writeText(json.encodeToString(HealthFile.serializer(), data)) }
    }

    private companion object {
        const val MAX_SNAPSHOTS = 60
        const val MIN_SNAPSHOTS = 3
        /** Awake share must worsen by this many percentage points to count. */
        const val AWAKE_POINTS_THRESHOLD = 5
        /** ~50 MB/day of extra background traffic. */
        const val BACKGROUND_BYTES_THRESHOLD = 50L * 1024 * 1024
    }
}
