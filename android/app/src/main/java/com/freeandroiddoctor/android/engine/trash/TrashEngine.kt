package com.freeandroiddoctor.android.engine.trash

import android.app.PendingIntent
import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import androidx.annotation.RequiresApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class TrashedItem(
    val uri: Uri,
    val displayName: String,
    val sizeBytes: Long,
    val mimeType: String,
    val dateExpires: Long,
)

/**
 * Browses and restores items currently in the system "Trash" of MediaStore (images, video,
 * audio and other media volumes). Trash is an Android 11+ concept; on older devices the
 * list is always empty and the system has no recycle bin to read from.
 */
class TrashEngine(private val context: Context) {

    suspend fun listTrashed(): List<TrashedItem> = withContext(Dispatchers.IO) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return@withContext emptyList()
        listTrashedApi30()
    }

    @RequiresApi(Build.VERSION_CODES.R)
    private fun listTrashedApi30(): List<TrashedItem> {
        val collection = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        val projection = arrayOf(
            MediaStore.Files.FileColumns._ID,
            MediaStore.Files.FileColumns.DISPLAY_NAME,
            MediaStore.Files.FileColumns.SIZE,
            MediaStore.Files.FileColumns.MIME_TYPE,
            MediaStore.Files.FileColumns.DATE_EXPIRES,
        )
        val queryArgs = android.os.Bundle().apply {
            putInt(MediaStore.QUERY_ARG_MATCH_TRASHED, MediaStore.MATCH_ONLY)
            putString(
                android.content.ContentResolver.QUERY_ARG_SQL_SORT_ORDER,
                "${MediaStore.Files.FileColumns.DATE_EXPIRES} DESC",
            )
        }
        val items = mutableListOf<TrashedItem>()
        context.contentResolver.query(collection, projection, queryArgs, null)?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns._ID)
            val nameCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.DISPLAY_NAME)
            val sizeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.SIZE)
            val mimeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.MIME_TYPE)
            val expCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.DATE_EXPIRES)
            while (c.moveToNext()) {
                val id = c.getLong(idCol)
                items += TrashedItem(
                    uri = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL, id),
                    displayName = c.getString(nameCol) ?: "?",
                    sizeBytes = c.getLong(sizeCol),
                    mimeType = c.getString(mimeCol).orEmpty(),
                    dateExpires = c.getLong(expCol),
                )
            }
        }
        return items
    }

    /** Builds a user-confirmation intent to take items out of the trash (Android 11+). */
    fun buildRestoreRequest(uris: List<Uri>): PendingIntent? {
        if (uris.isEmpty() || Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return null
        return MediaStore.createTrashRequest(context.contentResolver, uris, false)
    }

    /** Builds a permanent-delete confirmation for items the user wants to empty now. */
    fun buildPermanentDeleteRequest(uris: List<Uri>): PendingIntent? {
        if (uris.isEmpty() || Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return null
        return MediaStore.createDeleteRequest(context.contentResolver, uris)
    }

    /**
     * Best-effort move of an owned MediaStore item to trash without a system dialog.
     * Only works if this app owns the row (it would for files we created via SAF); used
     * for the "trash a single item from the cleaner" UX, not from the trash screen itself.
     */
    fun trashOwned(uri: Uri): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return false
        return runCatching {
            val values = ContentValues().apply { put(MediaStore.MediaColumns.IS_TRASHED, 1) }
            context.contentResolver.update(uri, values, null) > 0
        }.getOrDefault(false)
    }
}
