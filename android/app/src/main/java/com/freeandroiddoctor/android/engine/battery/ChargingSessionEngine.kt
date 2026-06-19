package com.freeandroiddoctor.android.engine.battery

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.util.concurrent.TimeUnit

@Serializable
data class ChargingSession(
    val startTs: Long,
    val endTs: Long,
    val fromPct: Int,
    val toPct: Int,
    val peakTempC: Float,
    val avgCurrentMa: Int,
    val estMahAdded: Int,
)

@Serializable
private data class SessionsFile(val items: List<ChargingSession> = emptyList())

/**
 * Append-only log of completed charging sessions. The active session is tracked in
 * memory by [com.freeandroiddoctor.android.service.ChargingSessionService]; only
 * finished sessions are persisted here.
 *
 * `estMahAdded` is integrated from real `current_now` samples (Σ i*dt / 3600) — no
 * fake mAh. If samples are missing the session still records pct delta and timing.
 */
class ChargingSessionEngine(context: Context) {

    private val dir = File(context.filesDir, "battery").apply { mkdirs() }
    private val file = File(dir, "sessions.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()
    private val _changes = MutableSharedFlow<Unit>(replay = 1, extraBufferCapacity = 4)
    val changes: Flow<Unit> = _changes

    init { _changes.tryEmit(Unit) }

    suspend fun append(session: ChargingSession) = withContext(Dispatchers.IO) {
        if (session.endTs <= session.startTs) return@withContext
        mutex.withLock {
            val current = readFile().items
            val pruned = current
                .filter { System.currentTimeMillis() - it.startTs <= RETENTION_MS }
                .takeLast(MAX - 1)
            writeFile(SessionsFile(pruned + session))
        }
        _changes.tryEmit(Unit)
    }

    suspend fun sessions(): List<ChargingSession> = withContext(Dispatchers.IO) {
        mutex.withLock { readFile().items.sortedByDescending { it.startTs } }
    }

    private fun readFile(): SessionsFile =
        if (!file.exists()) SessionsFile()
        else runCatching { json.decodeFromString<SessionsFile>(file.readText()) }
            .getOrElse { SessionsFile() }

    private fun writeFile(data: SessionsFile) {
        runCatching { file.writeText(json.encodeToString(SessionsFile.serializer(), data)) }
    }

    private companion object {
        const val MAX = 200
        val RETENTION_MS: Long = TimeUnit.DAYS.toMillis(180)
    }
}
