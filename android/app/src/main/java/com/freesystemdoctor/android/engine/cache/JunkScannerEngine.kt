package com.freesystemdoctor.android.engine.cache

import android.app.PendingIntent
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import com.freesystemdoctor.android.core.result.CleanResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

enum class JunkCategory { APP_CACHE, APK, TEMP }

data class JunkItem(
    val uri: Uri,
    val displayName: String,
    val sizeBytes: Long,
    val category: JunkCategory,
)

data class JunkReport(
    val appCacheBytes: Long,
    val mediaItems: List<JunkItem>,
) {
    val reclaimableBytes: Long
        get() = appCacheBytes + mediaItems.sumOf { it.sizeBytes }
}

/**
 * Scans junk this app may legitimately clean without root:
 *  - this app's own cache directories (always cleanable)
 *  - leftover .apk install files and .tmp/.log files indexed by MediaStore
 *
 * Deleting MediaStore-indexed files the app did not create requires user consent on
 * Android 11+, so [buildDeleteRequest] returns a PendingIntent the UI must launch.
 */
class JunkScannerEngine(private val context: Context) {

    suspend fun scan(): JunkReport = withContext(Dispatchers.IO) {
        JunkReport(
            appCacheBytes = ownCacheBytes(),
            mediaItems = queryMediaJunk(),
        )
    }

    fun cleanAppCache(): CleanResult = runCatching {
        var freed = 0L
        var count = 0
        listOfNotNull(context.cacheDir, context.externalCacheDir).forEach { dir ->
            dir.walkBottomUp().forEach { file ->
                if (file != dir && file.isFile) {
                    freed += file.length()
                    if (file.delete()) count++
                }
            }
        }
        CleanResult(itemsRemoved = count, bytesFreed = freed)
    }.getOrElse { CleanResult(itemsRemoved = 0, bytesFreed = 0, failures = 1) }

    /**
     * Builds a system delete-confirmation request for the given MediaStore items
     * (Android 11+). On older versions returns null and callers should use [deleteLegacy].
     */
    fun buildDeleteRequest(uris: List<Uri>): PendingIntent? {
        if (uris.isEmpty()) return null
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            MediaStore.createDeleteRequest(context.contentResolver, uris)
        } else {
            null
        }
    }

    fun deleteLegacy(uris: List<Uri>): CleanResult {
        var count = 0
        uris.forEach { uri ->
            runCatching { if (context.contentResolver.delete(uri, null, null) > 0) count++ }
        }
        return CleanResult(itemsRemoved = count, bytesFreed = 0)
    }

    private fun ownCacheBytes(): Long {
        return listOfNotNull(context.cacheDir, context.externalCacheDir)
            .sumOf { dir -> dir.walkTopDown().filter(File::isFile).sumOf { it.length() } }
    }

    private fun queryMediaJunk(): List<JunkItem> {
        val collection = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        val projection = arrayOf(
            MediaStore.Files.FileColumns._ID,
            MediaStore.Files.FileColumns.DISPLAY_NAME,
            MediaStore.Files.FileColumns.SIZE,
            MediaStore.Files.FileColumns.MIME_TYPE,
        )
        val selection = "${MediaStore.Files.FileColumns.MIME_TYPE} = ? OR " +
            "${MediaStore.Files.FileColumns.DISPLAY_NAME} LIKE ? OR " +
            "${MediaStore.Files.FileColumns.DISPLAY_NAME} LIKE ?"
        val args = arrayOf("application/vnd.android.package-archive", "%.tmp", "%.log")

        val items = mutableListOf<JunkItem>()
        context.contentResolver.query(collection, projection, selection, args, null)?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns._ID)
            val nameCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.DISPLAY_NAME)
            val sizeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.SIZE)
            val mimeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.MIME_TYPE)
            while (c.moveToNext()) {
                val id = c.getLong(idCol)
                val name = c.getString(nameCol) ?: continue
                val size = c.getLong(sizeCol)
                val mime = c.getString(mimeCol).orEmpty()
                val category = if (mime == "application/vnd.android.package-archive") {
                    JunkCategory.APK
                } else {
                    JunkCategory.TEMP
                }
                items += JunkItem(
                    uri = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL, id),
                    displayName = name,
                    sizeBytes = size,
                    category = category,
                )
            }
        }
        return items.sortedByDescending { it.sizeBytes }
    }
}
