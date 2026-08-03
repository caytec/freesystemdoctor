package com.freeandroiddoctor.android.engine.media

import android.content.ContentValues
import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.exifinterface.media.ExifInterface
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlin.coroutines.coroutineContext

/** Result of scrubbing one image. */
data class StripOutcome(
    val originalName: String,
    val success: Boolean,
    val hadLocation: Boolean,
    val cleanedUri: Uri? = null,
    val error: String? = null,
)

data class StripProgress(val done: Int, val total: Int, val currentName: String)

/**
 * Removes location and other identifying metadata (EXIF) from photos, writing a
 * clean COPY so the original is never touched. Everything runs on-device — no
 * network, no server.
 *
 * Approach per image:
 *  1. Byte-copy the original into a new MediaStore entry (Pictures/FreeAndroidDoctor/clean).
 *  2. Strip EXIF on the copy in place with [ExifInterface] (lossless for JPEG).
 *  3. If the format doesn't support in-place EXIF writes, fall back to a
 *     decode→re-encode, which drops all metadata inherently.
 *
 * The user selects photos via the system photo picker, so no storage permission
 * is required.
 */
class MetadataStripperEngine(private val context: Context) {

    /** EXIF tags that can identify where/when/with-what a photo was taken. */
    private val sensitiveTags = listOf(
        ExifInterface.TAG_GPS_LATITUDE,
        ExifInterface.TAG_GPS_LATITUDE_REF,
        ExifInterface.TAG_GPS_LONGITUDE,
        ExifInterface.TAG_GPS_LONGITUDE_REF,
        ExifInterface.TAG_GPS_ALTITUDE,
        ExifInterface.TAG_GPS_ALTITUDE_REF,
        ExifInterface.TAG_GPS_TIMESTAMP,
        ExifInterface.TAG_GPS_DATESTAMP,
        ExifInterface.TAG_GPS_PROCESSING_METHOD,
        ExifInterface.TAG_DATETIME,
        ExifInterface.TAG_DATETIME_ORIGINAL,
        ExifInterface.TAG_DATETIME_DIGITIZED,
        ExifInterface.TAG_MAKE,
        ExifInterface.TAG_MODEL,
        ExifInterface.TAG_SOFTWARE,
        ExifInterface.TAG_ARTIST,
        ExifInterface.TAG_COPYRIGHT,
        ExifInterface.TAG_USER_COMMENT,
        ExifInterface.TAG_IMAGE_DESCRIPTION,
        ExifInterface.TAG_SUBSEC_TIME,
    )

    /** True if the source image carries a GPS location tag. */
    private fun hasLocation(uri: Uri): Boolean = runCatching {
        context.contentResolver.openInputStream(uri)?.use { input ->
            val exif = ExifInterface(input)
            exif.latLong != null ||
                exif.getAttribute(ExifInterface.TAG_GPS_LATITUDE) != null
        } ?: false
    }.getOrDefault(false)

    /**
     * Scrubs each [uris] entry into a clean copy. Emits [onProgress] before each
     * file and returns per-file outcomes. Cancellable between files.
     */
    suspend fun stripAll(
        uris: List<Uri>,
        onProgress: (StripProgress) -> Unit = {},
    ): List<StripOutcome> = withContext(Dispatchers.IO) {
        uris.mapIndexed { index, uri ->
            coroutineContext.ensureActive()
            val name = displayName(uri)
            onProgress(StripProgress(index, uris.size, name))
            stripOne(uri, name)
        }
    }

    private fun stripOne(source: Uri, name: String): StripOutcome {
        val hadLocation = hasLocation(source)
        return runCatching {
            val mime = context.contentResolver.getType(source) ?: "image/jpeg"
            val cleanName = buildCleanName(name)
            val target = insertPending(cleanName, mime)
                ?: error("insert_failed")

            // 1. Byte-copy original → clean copy.
            context.contentResolver.openInputStream(source)?.use { input ->
                context.contentResolver.openOutputStream(target)?.use { output ->
                    input.copyTo(output)
                }
            } ?: error("copy_failed")

            // 2. Strip EXIF in place on the copy; fall back to re-encode.
            val stripped = stripExifInPlace(target)
            if (!stripped) reEncode(source, target, mime)

            markReady(target)
            StripOutcome(name, success = true, hadLocation = hadLocation, cleanedUri = target)
        }.getOrElse {
            StripOutcome(name, success = false, hadLocation = hadLocation, error = it.message)
        }
    }

    /** Returns true if EXIF was cleared in place; false if the format is unsupported. */
    private fun stripExifInPlace(target: Uri): Boolean = runCatching {
        context.contentResolver.openFileDescriptor(target, "rw")?.use { pfd ->
            val exif = ExifInterface(pfd.fileDescriptor)
            sensitiveTags.forEach { exif.setAttribute(it, null) }
            exif.saveAttributes()
        }
        true
    }.getOrDefault(false)

    /**
     * Fallback for formats ExifInterface can't rewrite (e.g. some WebP/HEIC):
     * decode and re-encode, which drops every metadata block. Downsampled to keep
     * memory bounded on low-end devices.
     */
    private fun reEncode(source: Uri, target: Uri, mime: String) {
        val opts = BitmapFactory.Options().apply { inSampleSize = 1 }
        val bitmap = context.contentResolver.openInputStream(source)?.use {
            BitmapFactory.decodeStream(it, null, opts)
        } ?: error("decode_failed")
        val format = if (mime.contains("png")) {
            android.graphics.Bitmap.CompressFormat.PNG
        } else {
            android.graphics.Bitmap.CompressFormat.JPEG
        }
        context.contentResolver.openOutputStream(target, "wt")?.use { out ->
            bitmap.compress(format, 95, out)
        }
        bitmap.recycle()
    }

    private fun buildCleanName(original: String): String {
        val base = original.substringBeforeLast('.', original)
        val ext = original.substringAfterLast('.', "jpg")
        return "${base}_clean.$ext"
    }

    private fun insertPending(name: String, mime: String): Uri? {
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, name)
            put(MediaStore.Images.Media.MIME_TYPE, mime)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(
                    MediaStore.Images.Media.RELATIVE_PATH,
                    "${Environment.DIRECTORY_PICTURES}/FreeAndroidDoctor/clean",
                )
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
        }
        return context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
    }

    private fun markReady(uri: Uri) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) }
            context.contentResolver.update(uri, values, null, null)
        }
    }

    private fun displayName(uri: Uri): String = runCatching {
        context.contentResolver.query(
            uri,
            arrayOf(MediaStore.Images.Media.DISPLAY_NAME),
            null, null, null,
        )?.use { c ->
            if (c.moveToFirst()) c.getString(0) else null
        }
    }.getOrNull() ?: (uri.lastPathSegment ?: "photo.jpg")
}
