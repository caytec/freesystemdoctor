package com.freesystemdoctor.android.engine.largefiles

import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class MediaFile(
    val uri: Uri,
    val displayName: String,
    val sizeBytes: Long,
    val mimeType: String,
)

class LargeFilesEngine(private val context: Context) {

    /** Returns media files larger than [minBytes], biggest first. */
    suspend fun findLargeFiles(
        minBytes: Long = 50L * 1024 * 1024,
        limit: Int = 200,
    ): List<MediaFile> = withContext(Dispatchers.IO) {
        val collection = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        val projection = arrayOf(
            MediaStore.Files.FileColumns._ID,
            MediaStore.Files.FileColumns.DISPLAY_NAME,
            MediaStore.Files.FileColumns.SIZE,
            MediaStore.Files.FileColumns.MIME_TYPE,
        )
        val selection = "${MediaStore.Files.FileColumns.SIZE} >= ?"
        val args = arrayOf(minBytes.toString())
        val sortOrder = "${MediaStore.Files.FileColumns.SIZE} DESC"

        val result = mutableListOf<MediaFile>()
        context.contentResolver.query(collection, projection, selection, args, sortOrder)?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns._ID)
            val nameCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.DISPLAY_NAME)
            val sizeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.SIZE)
            val mimeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.MIME_TYPE)
            while (c.moveToNext() && result.size < limit) {
                val id = c.getLong(idCol)
                result += MediaFile(
                    uri = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL, id),
                    displayName = c.getString(nameCol) ?: "",
                    sizeBytes = c.getLong(sizeCol),
                    mimeType = c.getString(mimeCol).orEmpty(),
                )
            }
        }
        result
    }
}
