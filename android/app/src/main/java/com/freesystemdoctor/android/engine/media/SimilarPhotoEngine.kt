package com.freesystemdoctor.android.engine.media

import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import com.freesystemdoctor.android.core.result.ScanProgress
import com.freesystemdoctor.android.core.util.Hashing
import com.freesystemdoctor.android.core.util.ImageSampler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class PhotoItem(
    val uri: Uri,
    val displayName: String,
    val sizeBytes: Long,
    val relativePath: String = "",
)

data class SimilarGroup(val items: List<PhotoItem>) {
    /** Bytes reclaimable by keeping a single photo from the group. */
    val reclaimableBytes: Long get() = items.drop(1).sumOf { it.sizeBytes }
}

/**
 * Groups visually-similar photos using a 64-bit average hash and Hamming distance.
 * Fully on-device, no extra libraries.
 */
class SimilarPhotoEngine(private val context: Context) {

    suspend fun findSimilar(
        threshold: Int = 8,
        limit: Int = 2000,
        progress: (ScanProgress) -> Unit = {},
    ): List<SimilarGroup> = withContext(Dispatchers.IO) {
        val photos = queryImages(limit)
        val hashed = ArrayList<Pair<PhotoItem, Long>>(photos.size)
        photos.forEachIndexed { index, photo ->
            progress(ScanProgress(index + 1, photos.size, photo.displayName))
            val pixels = ImageSampler.grayscale8x8(context, photo.uri) ?: return@forEachIndexed
            hashed += photo to Hashing.averageHash(pixels)
        }

        val used = BooleanArray(hashed.size)
        val groups = ArrayList<SimilarGroup>()
        for (i in hashed.indices) {
            if (used[i]) continue
            val members = ArrayList<PhotoItem>()
            members += hashed[i].first
            used[i] = true
            for (j in i + 1 until hashed.size) {
                if (used[j]) continue
                if (Hashing.hammingDistance(hashed[i].second, hashed[j].second) <= threshold) {
                    members += hashed[j].first
                    used[j] = true
                }
            }
            if (members.size > 1) {
                groups += SimilarGroup(members.sortedByDescending { it.sizeBytes })
            }
        }
        groups.sortedByDescending { it.reclaimableBytes }
    }

    private fun queryImages(limit: Int): List<PhotoItem> {
        val collection = MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DISPLAY_NAME,
            MediaStore.Images.Media.SIZE,
        )
        val sort = "${MediaStore.Images.Media.DATE_TAKEN} DESC"
        val out = ArrayList<PhotoItem>()
        context.contentResolver.query(collection, projection, null, null, sort)?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
            val nameCol = c.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME)
            val sizeCol = c.getColumnIndexOrThrow(MediaStore.Images.Media.SIZE)
            while (c.moveToNext() && out.size < limit) {
                val id = c.getLong(idCol)
                out += PhotoItem(
                    uri = MediaStore.Images.Media.EXTERNAL_CONTENT_URI.buildUpon()
                        .appendPath(id.toString()).build(),
                    displayName = c.getString(nameCol) ?: "",
                    sizeBytes = c.getLong(sizeCol),
                )
            }
        }
        return out
    }
}
