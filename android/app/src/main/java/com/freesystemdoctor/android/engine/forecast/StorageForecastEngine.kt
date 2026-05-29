package com.freesystemdoctor.android.engine.forecast

import android.content.Context
import com.freesystemdoctor.android.engine.storage.StorageAnalyzerEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.util.concurrent.TimeUnit
import kotlin.math.absoluteValue

@Serializable
data class Snapshot(val timestamp: Long, val freeBytes: Long)

@Serializable
private data class SnapshotsFile(val items: List<Snapshot> = emptyList())

data class ForecastResult(
    val freeNowBytes: Long,
    val totalBytes: Long,
    val snapshots: List<Snapshot>,
    /** Bytes per millisecond; negative = depletion. */
    val slope: Double?,
    val daysUntilFull: Long?,
    val state: State,
) {
    enum class State { GATHERING, NO_TREND, OVER_YEAR, COUNTDOWN }
}

/**
 * Persists a daily free-storage snapshot in a JSON file under [Context.getFilesDir] (~ a few
 * hundred bytes total for 30 days). Computes a trimmed-least-squares slope on the recent
 * window to forecast how many days until the volume fills up.
 *
 * Why a JSON file and not Room: a single suspending Mutex-guarded reader/writer pair is enough
 * for one row per day (max ~30 rows kept); Room would be over-engineered.
 */
class StorageForecastEngine(
    private val context: Context,
    private val storage: StorageAnalyzerEngine,
) {

    private val dir = File(context.filesDir, "forecast").apply { mkdirs() }
    private val file = File(dir, "snapshots.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()

    suspend fun recordToday(): Snapshot = withContext(Dispatchers.IO) {
        mutex.withLock {
            val volume = storage.readPrimaryVolume()
            val now = System.currentTimeMillis()
            val existing = readFile()
            // De-dup same-day entries (keep newest per day).
            val pruned = existing.items
                .filter { sameDay(it.timestamp, now).not() }
                .filter { now - it.timestamp <= TimeUnit.DAYS.toMillis(RETENTION_DAYS.toLong()) }
            val updated = pruned + Snapshot(now, volume.freeBytes)
            writeFile(SnapshotsFile(updated))
            updated.last()
        }
    }

    suspend fun forecast(window: Int = WINDOW_DAYS): ForecastResult = withContext(Dispatchers.IO) {
        val volume = storage.readPrimaryVolume()
        val items = mutex.withLock { readFile().items }
        val cutoff = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(window.toLong())
        val recent = items.filter { it.timestamp >= cutoff }.sortedBy { it.timestamp }

        if (recent.size < MIN_POINTS) {
            return@withContext ForecastResult(
                freeNowBytes = volume.freeBytes,
                totalBytes = volume.totalBytes,
                snapshots = recent,
                slope = null,
                daysUntilFull = null,
                state = ForecastResult.State.GATHERING,
            )
        }

        // Trimmed least-squares: drop biggest +Δ and biggest −Δ if we have headroom.
        val fitInput = if (recent.size >= 10) trimOutliers(recent) else recent
        val slope = leastSquaresSlope(fitInput)

        if (slope >= 0.0) {
            return@withContext ForecastResult(
                freeNowBytes = volume.freeBytes,
                totalBytes = volume.totalBytes,
                snapshots = recent,
                slope = slope,
                daysUntilFull = null,
                state = ForecastResult.State.NO_TREND,
            )
        }

        val msPerDay = TimeUnit.DAYS.toMillis(1).toDouble()
        val daysRaw = volume.freeBytes / (slope.absoluteValue * msPerDay)
        val days = daysRaw.toLong().coerceAtLeast(0)
        return@withContext if (days >= 365) {
            ForecastResult(
                freeNowBytes = volume.freeBytes,
                totalBytes = volume.totalBytes,
                snapshots = recent,
                slope = slope,
                daysUntilFull = days,
                state = ForecastResult.State.OVER_YEAR,
            )
        } else {
            ForecastResult(
                freeNowBytes = volume.freeBytes,
                totalBytes = volume.totalBytes,
                snapshots = recent,
                slope = slope,
                daysUntilFull = days,
                state = ForecastResult.State.COUNTDOWN,
            )
        }
    }

    private fun trimOutliers(items: List<Snapshot>): List<Snapshot> {
        val deltas = items.zipWithNext { a, b -> b.freeBytes - a.freeBytes }
        if (deltas.isEmpty()) return items
        val maxIdx = deltas.indices.maxByOrNull { deltas[it] } ?: -1
        val minIdx = deltas.indices.minByOrNull { deltas[it] } ?: -1
        val toDrop = setOfNotNull(
            (maxIdx + 1).takeIf { it in items.indices },
            (minIdx + 1).takeIf { it in items.indices && it != maxIdx + 1 },
        )
        return items.filterIndexed { idx, _ -> idx !in toDrop }
    }

    /** Returns slope in bytes per ms (negative = depleting). */
    private fun leastSquaresSlope(points: List<Snapshot>): Double {
        val n = points.size
        val meanX = points.sumOf { it.timestamp.toDouble() } / n
        val meanY = points.sumOf { it.freeBytes.toDouble() } / n
        var num = 0.0
        var den = 0.0
        points.forEach { p ->
            val dx = p.timestamp - meanX
            val dy = p.freeBytes - meanY
            num += dx * dy
            den += dx * dx
        }
        return if (den == 0.0) 0.0 else num / den
    }

    private fun readFile(): SnapshotsFile =
        if (file.exists()) {
            runCatching { json.decodeFromString(SnapshotsFile.serializer(), file.readText()) }
                .getOrDefault(SnapshotsFile())
        } else SnapshotsFile()

    private fun writeFile(data: SnapshotsFile) {
        file.writeText(json.encodeToString(SnapshotsFile.serializer(), data))
    }

    private fun sameDay(a: Long, b: Long): Boolean =
        a / TimeUnit.DAYS.toMillis(1) == b / TimeUnit.DAYS.toMillis(1)

    private companion object {
        const val RETENTION_DAYS = 30
        const val WINDOW_DAYS = 14
        const val MIN_POINTS = 7
    }
}
