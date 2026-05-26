package com.freesystemdoctor.android.engine.files

import android.content.Context
import android.net.Uri
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.security.SecureRandom

data class ShredResult(val success: Boolean, val name: String, val passes: Int, val error: String? = null)

/**
 * Best-effort secure delete: overwrites a file's bytes with random data before
 * deleting it. Honest caveat surfaced in the UI — on flash storage with wear
 * levelling, overwriting logical blocks does not guarantee physical erasure.
 * Only works for files the user opened with write access (SAF document URIs).
 */
class FileShredderEngine(private val context: Context) {

    fun displayName(uri: Uri): String {
        var name = uri.lastPathSegment ?: "file"
        runCatching {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
                ?.use { c -> if (c.moveToFirst()) name = c.getString(0) ?: name }
        }
        return name
    }

    suspend fun shred(uri: Uri, passes: Int = 3): ShredResult = withContext(Dispatchers.IO) {
        val name = displayName(uri)
        runCatching {
            val size = querySize(uri)
            if (size > 0) {
                val random = SecureRandom()
                val buffer = ByteArray(64 * 1024)
                repeat(passes) {
                    context.contentResolver.openOutputStream(uri, "rwt")?.use { out ->
                        var written = 0L
                        while (written < size) {
                            random.nextBytes(buffer)
                            val toWrite = minOf(buffer.size.toLong(), size - written).toInt()
                            out.write(buffer, 0, toWrite)
                            written += toWrite
                        }
                        out.flush()
                    } ?: error("no_write_access")
                }
            }
            val deleted = runCatching {
                DocumentsContract.deleteDocument(context.contentResolver, uri)
            }.getOrElse { context.contentResolver.delete(uri, null, null) > 0 }
            if (!deleted) error("delete_failed")
            ShredResult(success = true, name = name, passes = passes)
        }.getOrElse { ShredResult(success = false, name = name, passes = passes, error = it.message) }
    }

    private fun querySize(uri: Uri): Long {
        var size = 0L
        runCatching {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)
                ?.use { c -> if (c.moveToFirst()) size = c.getLong(0) }
        }
        return size
    }
}
