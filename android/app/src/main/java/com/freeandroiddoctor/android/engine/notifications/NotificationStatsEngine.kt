package com.freeandroiddoctor.android.engine.notifications

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.util.concurrent.TimeUnit

@Serializable
data class NotificationEvent(val ts: Long, val packageName: String)

@Serializable
private data class StatsFile(val events: List<NotificationEvent> = emptyList())

data class AppNotifCount(val packageName: String, val count: Int, val label: String = packageName)

/**
 * Persists notification post events from [com.freeandroiddoctor.android.service.FsdNotificationListener].
 * Bounded by [MAX_EVENTS] (oldest first dropped) so a chatty app can't grow the file unboundedly.
 *
 * Storage lives in `filesDir/notif_stats/stats.json` and is touched from the listener
 * thread with a Mutex.
 */
class NotificationStatsEngine(context: Context) {

    private val appContext = context.applicationContext
    private val dir = File(context.filesDir, "notif_stats").apply { mkdirs() }
    private val file = File(dir, "stats.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()
    private val pending = ArrayList<NotificationEvent>()

    /** Lightweight — buffers in memory; persistence happens on demand. */
    fun record(packageName: String) {
        if (packageName.isBlank()) return
        synchronized(pending) {
            pending += NotificationEvent(System.currentTimeMillis(), packageName)
        }
    }

    suspend fun flush() = withContext(Dispatchers.IO) {
        val toFlush: List<NotificationEvent> = synchronized(pending) {
            if (pending.isEmpty()) return@withContext
            val copy = pending.toList()
            pending.clear()
            copy
        }
        mutex.withLock {
            val current = readFile().events
            val merged = current + toFlush
            val cutoff = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(7)
            val pruned = merged.filter { it.ts >= cutoff }.takeLast(MAX_EVENTS)
            writeFile(StatsFile(pruned))
        }
    }

    suspend fun topApps(limit: Int = 50): List<AppNotifCount> = withContext(Dispatchers.IO) {
        flush()
        val counts = mutex.withLock {
            val cutoff = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(7)
            readFile().events
                .filter { it.ts >= cutoff }
                .groupingBy { it.packageName }
                .eachCount()
                .entries.sortedByDescending { it.value }
                .take(limit)
                .map { it.key to it.value }
        }
        // Resolve labels here (IO) so list-item composition does no binder work.
        val pm = appContext.packageManager
        counts.map { (pkg, count) ->
            val label = runCatching {
                pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString()
            }.getOrDefault(pkg)
            AppNotifCount(pkg, count, label)
        }
    }

    private fun readFile(): StatsFile =
        if (!file.exists()) StatsFile()
        else runCatching { json.decodeFromString<StatsFile>(file.readText()) }.getOrElse { StatsFile() }

    private fun writeFile(data: StatsFile) {
        runCatching { file.writeText(json.encodeToString(StatsFile.serializer(), data)) }
    }

    private companion object { const val MAX_EVENTS = 2000 }
}
