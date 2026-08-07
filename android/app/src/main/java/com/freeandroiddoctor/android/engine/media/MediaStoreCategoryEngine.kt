package com.freeandroiddoctor.android.engine.media

import android.content.Context
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

enum class MediaCategory { IMAGES, VIDEO, AUDIO, DOCUMENTS, ARCHIVES, OTHER }

data class CategoryUsage(
    val category: MediaCategory,
    val count: Int,
    val totalBytes: Long,
)

/**
 * Aggregates shared-storage usage by file type via a single MediaStore.Files query.
 * No special permission beyond the granted media read access.
 */
class MediaStoreCategoryEngine(private val context: Context) {

    suspend fun scan(): List<CategoryUsage> = withContext(Dispatchers.IO) {
        val counts = HashMap<MediaCategory, Int>()
        val sizes = HashMap<MediaCategory, Long>()

        val collection = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        val projection = arrayOf(
            MediaStore.Files.FileColumns.SIZE,
            MediaStore.Files.FileColumns.MIME_TYPE,
            MediaStore.Files.FileColumns.DISPLAY_NAME,
        )
        context.contentResolver.query(collection, projection, null, null, null)?.use { c ->
            val sizeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.SIZE)
            val mimeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.MIME_TYPE)
            val nameCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.DISPLAY_NAME)
            while (c.moveToNext()) {
                val size = c.getLong(sizeCol)
                val mime = c.getString(mimeCol).orEmpty()
                val name = c.getString(nameCol).orEmpty()
                val cat = categorize(mime, name)
                counts[cat] = (counts[cat] ?: 0) + 1
                sizes[cat] = (sizes[cat] ?: 0L) + size
            }
        }

        MediaCategory.entries
            .map { CategoryUsage(it, counts[it] ?: 0, sizes[it] ?: 0L) }
            .filter { it.count > 0 }
            .sortedByDescending { it.totalBytes }
    }

    private fun categorize(mime: String, name: String): MediaCategory = when {
        mime.startsWith("image/") -> MediaCategory.IMAGES
        mime.startsWith("video/") -> MediaCategory.VIDEO
        mime.startsWith("audio/") -> MediaCategory.AUDIO
        mime.startsWith("text/") ||
            mime.contains("pdf") ||
            mime.contains("word") ||
            mime.contains("document") ||
            mime.contains("sheet") ||
            mime.contains("presentation") -> MediaCategory.DOCUMENTS
        mime.contains("zip") ||
            mime.contains("rar") ||
            mime.contains("compressed") ||
            mime.contains("archive") ||
            name.endsWith(".apk", true) -> MediaCategory.ARCHIVES
        else -> MediaCategory.OTHER
    }
}
