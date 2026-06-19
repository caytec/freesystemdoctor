package com.freeandroiddoctor.android.engine.files

import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import com.freeandroiddoctor.android.core.result.CleanResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

data class LogFile(
    val uri: Uri?,
    val displayName: String,
    val sizeBytes: Long,
    val source: LogSource,
)

enum class LogSource { OWN_APP, MEDIA_STORE, SHIZUKU }

data class LogReport(
    val files: List<LogFile>,
    val ownAppBytes: Long,
    val mediaStoreBytes: Long,
    val shizukuBytes: Long,
) {
    val totalBytes: Long get() = ownAppBytes + mediaStoreBytes + shizukuBytes
}

/**
 * Finds log / ANR / tombstone / stacktrace files this app can clean (or at least surface) without
 * root. Three tiers, in order of certainty:
 *  1. Own-app: walks {@code cacheDir}, {@code filesDir/logs}, {@code noBackupFilesDir}. Always works,
 *     always free. Returned files can be deleted directly.
 *  2. MediaStore: text/log files indexed externally. The {@code TEMP_SCAN} phase in
 *     [com.freeandroiddoctor.android.engine.cache.JunkScannerEngine] already counts `*.log` and
 *     `*.tmp`; we de-dup at construction time so the same file is never counted twice. We pick
 *     `*.anr`, `*.tombstone`, `*.stacktrace` here.
 *  3. Shizuku (if available): walks `/data/anr` and `/data/tombstones` via the shim. Silent
 *     fallback when not available — not even attempted.
 */
class LogFilesEngine(private val context: Context) {

    suspend fun scan(shizukuAvailable: Boolean = false): LogReport = withContext(Dispatchers.IO) {
        val files = ArrayList<LogFile>()
        val ownBytes = scanOwnApp(files)
        val mediaBytes = scanMediaStore(files)
        val shizukuBytes = if (shizukuAvailable) scanShizuku(files) else 0L
        LogReport(
            files = files.sortedByDescending { it.sizeBytes },
            ownAppBytes = ownBytes,
            mediaStoreBytes = mediaBytes,
            shizukuBytes = shizukuBytes,
        )
    }

    /** Deletes own-app log files only — the other tiers stay read-only by design. */
    suspend fun cleanOwnApp(): CleanResult = withContext(Dispatchers.IO) {
        var bytes = 0L
        var count = 0
        ownAppLogDirs().forEach { dir ->
            dir.walkBottomUp().forEach { file ->
                if (file.isFile && hasLogExtension(file.name)) {
                    val size = file.length()
                    if (file.delete()) {
                        bytes += size
                        count++
                    }
                }
            }
        }
        CleanResult(itemsRemoved = count, bytesFreed = bytes)
    }

    private fun scanOwnApp(out: MutableList<LogFile>): Long {
        var total = 0L
        ownAppLogDirs().forEach { dir ->
            dir.walkTopDown().forEach { file ->
                if (file.isFile && hasLogExtension(file.name)) {
                    val size = file.length()
                    total += size
                    out += LogFile(null, file.name, size, LogSource.OWN_APP)
                }
            }
        }
        return total
    }

    private fun scanMediaStore(out: MutableList<LogFile>): Long {
        val collection = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        val projection = arrayOf(
            MediaStore.Files.FileColumns._ID,
            MediaStore.Files.FileColumns.DISPLAY_NAME,
            MediaStore.Files.FileColumns.SIZE,
        )
        // We claim crash-specific extensions ONLY; JunkScannerEngine already covers .log + .tmp.
        val selection = (LOG_EXTENSIONS_MEDIA_STORE.joinToString(" OR ") {
            "${MediaStore.Files.FileColumns.DISPLAY_NAME} LIKE ?"
        })
        val args = LOG_EXTENSIONS_MEDIA_STORE.map { "%$it" }.toTypedArray()

        var total = 0L
        runCatching {
            context.contentResolver.query(collection, projection, selection, args, null)?.use { c ->
                val idCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns._ID)
                val nameCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.DISPLAY_NAME)
                val sizeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.SIZE)
                while (c.moveToNext()) {
                    val id = c.getLong(idCol)
                    val name = c.getString(nameCol) ?: continue
                    val size = c.getLong(sizeCol)
                    total += size
                    out += LogFile(
                        uri = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL, id),
                        displayName = name,
                        sizeBytes = size,
                        source = LogSource.MEDIA_STORE,
                    )
                }
            }
        }
        return total
    }

    @Suppress("UNUSED_PARAMETER")
    private fun scanShizuku(out: MutableList<LogFile>): Long {
        // The real Shizuku binding is deferred (see ShizukuManager). Once the dep is flipped, this
        // walks /data/anr and /data/tombstones via the shim. Until then, the engine reports 0L.
        return 0L
    }

    private fun ownAppLogDirs(): List<File> {
        val out = mutableListOf<File>()
        context.cacheDir?.let { out += it }
        context.filesDir?.let { base ->
            File(base, "logs").takeIf { it.exists() }?.let { out += it }
        }
        runCatching { context.noBackupFilesDir }.getOrNull()?.let { out += it }
        return out.distinct()
    }

    private fun hasLogExtension(name: String): Boolean {
        val lower = name.lowercase()
        return OWN_APP_LOG_EXTENSIONS.any { lower.endsWith(it) }
    }

    private companion object {
        // Own-app tier covers more (we own these bytes, deleting is safe).
        val OWN_APP_LOG_EXTENSIONS = listOf(
            ".log", ".anr", ".tombstone", ".stacktrace",
        )
        // MediaStore tier intentionally EXCLUDES .log and .tmp — those are JunkScannerEngine's
        // territory (TEMP_SCAN phase). We pick crash-specific extensions only.
        val LOG_EXTENSIONS_MEDIA_STORE = listOf(
            ".anr", ".tombstone", ".stacktrace",
        )
    }
}
