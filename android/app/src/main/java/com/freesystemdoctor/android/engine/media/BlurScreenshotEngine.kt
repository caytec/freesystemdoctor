package com.freesystemdoctor.android.engine.media

import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import com.freesystemdoctor.android.core.result.ScanProgress
import com.freesystemdoctor.android.core.util.ImageSampler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class PhotoReview(
    val screenshots: List<PhotoItem>,
    val blurry: List<PhotoItem>,
)

/**
 * Finds screenshots (by path/name) and blurry photos (low Laplacian variance).
 * Both are common cleanup candidates; nothing is deleted without user consent.
 */
class BlurScreenshotEngine(private val context: Context) {

    suspend fun review(
        blurThreshold: Double = 120.0,
        blurScanLimit: Int = 1000,
        progress: (ScanProgress) -> Unit = {},
    ): PhotoReview = withContext(Dispatchers.IO) {
        val all = queryImages()
        val screenshots = all.filter { isScreenshot(it) }
        val blurry = ArrayList<PhotoItem>()
        val toScan = all.take(blurScanLimit)
        toScan.forEachIndexed { index, photo ->
            progress(ScanProgress(index + 1, toScan.size, photo.displayName))
            val variance = ImageSampler.laplacianVariance(context, photo.uri) ?: return@forEachIndexed
            if (variance < blurThreshold) blurry += photo
        }
        PhotoReview(
            screenshots = screenshots.sortedByDescending { it.sizeBytes },
            blurry = blurry.sortedByDescending { it.sizeBytes },
        )
    }

    private fun isScreenshot(item: PhotoItem): Boolean =
        item.displayName.startsWith("Screenshot", ignoreCase = true) ||
            item.relativePath.contains("Screenshots", ignoreCase = true)

    private fun queryImages(): List<PhotoItem> {
        val collection = MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        val hasRelPath = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q
        val projection = buildList {
            add(MediaStore.Images.Media._ID)
            add(MediaStore.Images.Media.DISPLAY_NAME)
            add(MediaStore.Images.Media.SIZE)
            if (hasRelPath) add(MediaStore.Images.Media.RELATIVE_PATH)
        }.toTypedArray()

        val out = ArrayList<PhotoItem>()
        context.contentResolver.query(collection, projection, null, null, null)?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
            val nameCol = c.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME)
            val sizeCol = c.getColumnIndexOrThrow(MediaStore.Images.Media.SIZE)
            val pathCol = if (hasRelPath) {
                c.getColumnIndex(MediaStore.Images.Media.RELATIVE_PATH)
            } else {
                -1
            }
            while (c.moveToNext()) {
                val id = c.getLong(idCol)
                out += PhotoItem(
                    uri = MediaStore.Images.Media.EXTERNAL_CONTENT_URI.buildUpon()
                        .appendPath(id.toString()).build(),
                    displayName = c.getString(nameCol) ?: "",
                    sizeBytes = c.getLong(sizeCol),
                    relativePath = if (pathCol >= 0) c.getString(pathCol).orEmpty() else "",
                )
            }
        }
        return out
    }
}
