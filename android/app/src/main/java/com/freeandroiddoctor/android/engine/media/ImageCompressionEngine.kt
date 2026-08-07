package com.freeandroiddoctor.android.engine.media

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

data class CompressResult(
    val success: Boolean,
    val name: String,
    val originalBytes: Long = 0,
    val newBytes: Long = 0,
    val error: String? = null,
) {
    val savedBytes: Long get() = (originalBytes - newBytes).coerceAtLeast(0)
}

/**
 * Re-encodes a photo at lower quality / capped dimensions into a new file under
 * Pictures/FreeAndroidDoctor. The original is left untouched so the user can delete it.
 */
class ImageCompressionEngine(private val context: Context) {

    suspend fun compress(
        item: PhotoItem,
        quality: Int = 75,
        maxDimension: Int = 2048,
    ): CompressResult = withContext(Dispatchers.IO) {
        runCatching {
            val bitmap = decode(item.uri, maxDimension) ?: error("decode_failed")
            val bytes = ByteArrayOutputStream().use { bos ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, quality, bos)
                bos.toByteArray()
            }
            bitmap.recycle()
            val name = "cmp_${item.displayName.substringBeforeLast('.')}.jpg"
            writeToPictures(name, bytes)
            CompressResult(
                success = true,
                name = name,
                originalBytes = item.sizeBytes,
                newBytes = bytes.size.toLong(),
            )
        }.getOrElse {
            CompressResult(success = false, name = item.displayName, error = it.message)
        }
    }

    private fun decode(uri: Uri, maxDimension: Int): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, bounds)
        }
        // Choose the smallest sample that brings BOTH dimensions to <= maxDimension.
        // The old `/(sample*2) >= max` condition stopped one step early and could
        // leave a bitmap ~2× maxDimension — up to ~64 MB ARGB_8888 → OOM on 2-3 GB
        // devices. inPreferredConfig=RGB_565 halves the decoded footprint; JPEG
        // output quality is unaffected for photos.
        var sample = 1
        while (bounds.outWidth / (sample * 2) >= maxDimension ||
            bounds.outHeight / (sample * 2) >= maxDimension
        ) {
            sample *= 2
        }
        val opts = BitmapFactory.Options().apply {
            inSampleSize = sample
            inPreferredConfig = Bitmap.Config.RGB_565
        }
        val decoded = context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, opts)
        } ?: return null

        // Guard: if the source dimensions were unavailable (outWidth <= 0), sampling
        // couldn't run — downscale in-memory as a fallback before returning.
        val longest = maxOf(decoded.width, decoded.height)
        if (longest <= maxDimension) return decoded
        val ratio = maxDimension.toFloat() / longest
        return Bitmap.createScaledBitmap(
            decoded,
            (decoded.width * ratio).toInt().coerceAtLeast(1),
            (decoded.height * ratio).toInt().coerceAtLeast(1),
            true,
        ).also { if (it !== decoded) decoded.recycle() }
    }

    private fun writeToPictures(name: String, bytes: ByteArray) {
        val resolver = context.contentResolver
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, name)
                put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                put(
                    MediaStore.Images.Media.RELATIVE_PATH,
                    "${Environment.DIRECTORY_PICTURES}/FreeAndroidDoctor",
                )
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
            val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: error("insert_failed")
            resolver.openOutputStream(uri)?.use { it.write(bytes) }
            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        } else {
            @Suppress("DEPRECATION")
            val dir = java.io.File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES),
                "FreeAndroidDoctor",
            ).apply { mkdirs() }
            java.io.File(dir, name).outputStream().use { it.write(bytes) }
        }
    }
}
