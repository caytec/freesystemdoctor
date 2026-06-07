package com.freesystemdoctor.android.engine.history

import android.content.Context
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

/** Which clean path produced this record (kept human-readable for CSV). */
enum class CleanSource {
    JUNK_CACHE,
    HIDDEN_CACHE,
    LARGE_FILES,
    DUPLICATES,
    PHOTOS,
    TRASH,
    CORPSE_FINDER,
    APP_DEEP_CLEAN,
    WHATSAPP_DEEP,
    TELEGRAM_DEEP,
    DISCORD_DEEP,
    TIKTOK_DEEP,
    SHIZUKU_FORCE_STOP,
    OTHER,
}

@Serializable
data class CleanRecord(
    val timestamp: Long,
    val source: String,
    val bytesFreed: Long,
    val itemsRemoved: Int,
)

@Serializable
private data class HistoryFile(val items: List<CleanRecord> = emptyList())

data class HistorySummary(
    val lifetimeBytesFreed: Long,
    val lifetimeItemsRemoved: Int,
    val last30dBytesFreed: Long,
    val last30dItemsRemoved: Int,
    val records: List<CleanRecord>,
)

/**
 * Append-only record of every clean the app performed, with real measured `bytesFreed` /
 * `itemsRemoved` returned by the underlying engines (no estimates, no inflation — honest
 * brand). Persisted as JSON under `filesDir/cleaning_history/history.json` with a Mutex.
 * The lifetime total is FREE (social proof). Full history view + CSV export are PRO.
 */
class CleaningHistoryEngine(context: Context) {

    private val dir = File(context.filesDir, "cleaning_history").apply { mkdirs() }
    private val file = File(dir, "history.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()
    private val _changes = MutableSharedFlow<Unit>(replay = 1, extraBufferCapacity = 4)
    val changes: Flow<Unit> = _changes

    init {
        _changes.tryEmit(Unit)
    }

    suspend fun recordClean(
        source: CleanSource,
        bytesFreed: Long,
        itemsRemoved: Int,
    ) = withContext(Dispatchers.IO) {
        if (bytesFreed <= 0 && itemsRemoved <= 0) return@withContext
        mutex.withLock {
            val current = readFile().items
            val pruned = current
                .filter { System.currentTimeMillis() - it.timestamp <= RETENTION_MS }
                .takeLast(MAX_RECORDS - 1)
            val updated = pruned + CleanRecord(
                timestamp = System.currentTimeMillis(),
                source = source.name,
                bytesFreed = bytesFreed.coerceAtLeast(0L),
                itemsRemoved = itemsRemoved.coerceAtLeast(0),
            )
            writeFile(HistoryFile(updated))
        }
        _changes.tryEmit(Unit)
    }

    suspend fun summary(): HistorySummary = withContext(Dispatchers.IO) {
        mutex.withLock {
            val items = readFile().items
            val cutoff = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(30)
            val recent = items.filter { it.timestamp >= cutoff }
            HistorySummary(
                lifetimeBytesFreed = items.sumOf { it.bytesFreed },
                lifetimeItemsRemoved = items.sumOf { it.itemsRemoved },
                last30dBytesFreed = recent.sumOf { it.bytesFreed },
                last30dItemsRemoved = recent.sumOf { it.itemsRemoved },
                records = items.sortedByDescending { it.timestamp },
            )
        }
    }

    suspend fun exportCsv(context: Context, target: Uri): Int = withContext(Dispatchers.IO) {
        val items = mutex.withLock { readFile().items }
        val resolver = context.contentResolver
        val dateFmt = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)
        resolver.openOutputStream(target, "w")?.use { out ->
            out.write("timestamp,source,bytes_freed,items_removed\n".toByteArray())
            items.forEach { rec ->
                val line = "${dateFmt.format(Date(rec.timestamp))}," +
                    "${rec.source},${rec.bytesFreed},${rec.itemsRemoved}\n"
                out.write(line.toByteArray())
            }
            out.flush()
        }
        items.size
    }

    private fun readFile(): HistoryFile {
        if (!file.exists()) return HistoryFile()
        return runCatching { json.decodeFromString<HistoryFile>(file.readText()) }
            .getOrElse { HistoryFile() }
    }

    private fun writeFile(data: HistoryFile) {
        runCatching { file.writeText(json.encodeToString(HistoryFile.serializer(), data)) }
    }

    private companion object {
        const val MAX_RECORDS = 500
        val RETENTION_MS: Long = TimeUnit.DAYS.toMillis(365)
    }
}
