package com.freeandroiddoctor.android.engine.forecast

import android.content.Context
import com.freeandroiddoctor.android.engine.storage.StorageAnalyzerEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.util.concurrent.TimeUnit

@Serializable
data class AppSizeSnapshot(
    val timestamp: Long,
    /** packageName → total bytes (app + data + cache). */
    val sizes: Map<String, Long>,
)

@Serializable
private data class GrowthFile(val snapshots: List<AppSizeSnapshot> = emptyList())

/** How much one app grew (or shrank) over the compared window. */
data class AppGrowth(
    val packageName: String,
    val label: String,
    val currentBytes: Long,
    val deltaBytes: Long,
)

data class GrowthReport(
    val growth: List<AppGrowth>,
    val windowDays: Int,
    val comparedAgainst: Long,
    val state: State,
) {
    enum class State { GATHERING, READY }
}

/**
 * Tracks per-app storage over time so the app can say "WhatsApp grew 2 GB this week".
 *
 * Competitors (and our own treemap / forecast) show a point-in-time picture or the total
 * free-space trend; nobody surfaces which individual app is quietly inflating. Snapshots
 * are written once a day by the existing storage worker and kept in a small local JSON
 * file — no network, no per-app history leaves the device.
 */
class AppGrowthEngine(
    context: Context,
    private val storage: StorageAnalyzerEngine,
) {

    private val dir = File(context.filesDir, "app_growth").apply { mkdirs() }
    private val file = File(dir, "snapshots.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()

    /** Records today's per-app sizes (at most one snapshot per calendar day). */
    suspend fun recordToday() = withContext(Dispatchers.IO) {
        val now = System.currentTimeMillis()
        mutex.withLock {
            val current = read().snapshots
            val last = current.lastOrNull()
            if (last != null && now - last.timestamp < TimeUnit.HOURS.toMillis(20)) return@withLock
            val sizes = runCatching { storage.readPerApp() }.getOrDefault(emptyList())
                // Cap the map so the file stays small on app-heavy devices.
                .sortedByDescending { it.totalBytes }
                .take(MAX_APPS)
                .associate { it.packageName to it.totalBytes }
            if (sizes.isEmpty()) return@withLock
            val pruned = (current + AppSizeSnapshot(now, sizes)).takeLast(MAX_SNAPSHOTS)
            write(GrowthFile(pruned))
        }
    }

    /**
     * Compares the newest snapshot with the oldest one inside [windowDays] and returns the
     * biggest growers first. Apps that shrank are included (negative delta) but ranked last.
     */
    suspend fun growth(windowDays: Int = 7, limit: Int = 25): GrowthReport =
        withContext(Dispatchers.IO) {
            val snapshots = mutex.withLock { read().snapshots }
            if (snapshots.size < 2) {
                return@withContext GrowthReport(
                    emptyList(), windowDays, 0L, GrowthReport.State.GATHERING,
                )
            }
            val newest = snapshots.last()
            val cutoff = newest.timestamp - TimeUnit.DAYS.toMillis(windowDays.toLong())
            // Oldest snapshot still inside the window, else the oldest we have.
            val baseline = snapshots.firstOrNull { it.timestamp >= cutoff }
                ?.takeIf { it.timestamp != newest.timestamp }
                ?: snapshots.first()
            if (baseline.timestamp == newest.timestamp) {
                return@withContext GrowthReport(
                    emptyList(), windowDays, 0L, GrowthReport.State.GATHERING,
                )
            }

            val labels = runCatching { storage.readPerApp() }.getOrDefault(emptyList())
                .associate { it.packageName to it.label }

            val items = newest.sizes.mapNotNull { (pkg, nowBytes) ->
                val before = baseline.sizes[pkg] ?: return@mapNotNull null
                val delta = nowBytes - before
                if (delta.absoluteValueCompat() < MIN_DELTA_BYTES) return@mapNotNull null
                AppGrowth(
                    packageName = pkg,
                    label = labels[pkg] ?: pkg,
                    currentBytes = nowBytes,
                    deltaBytes = delta,
                )
            }.sortedByDescending { it.deltaBytes }.take(limit)

            GrowthReport(
                growth = items,
                windowDays = windowDays,
                comparedAgainst = baseline.timestamp,
                state = GrowthReport.State.READY,
            )
        }

    private fun Long.absoluteValueCompat(): Long = if (this < 0) -this else this

    private fun read(): GrowthFile =
        if (!file.exists()) GrowthFile()
        else runCatching { json.decodeFromString<GrowthFile>(file.readText()) }
            .getOrElse { GrowthFile() }

    private fun write(data: GrowthFile) {
        runCatching { file.writeText(json.encodeToString(GrowthFile.serializer(), data)) }
    }

    private companion object {
        const val MAX_SNAPSHOTS = 30
        const val MAX_APPS = 100
        /** Ignore noise below ~20 MB so the list stays meaningful. */
        const val MIN_DELTA_BYTES = 20L * 1024 * 1024
    }
}
