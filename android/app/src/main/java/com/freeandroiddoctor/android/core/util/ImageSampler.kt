package com.freeandroiddoctor.android.core.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri

/** Lightweight image sampling for perceptual hashing and blur detection (no extra libs). */
object ImageSampler {

    /** 64 grayscale luminance samples (8x8) for average-hash, or null if undecodable. */
    fun grayscale8x8(context: Context, uri: Uri): IntArray? {
        val bitmap = decodeSampled(context, uri, 64) ?: return null
        val scaled = Bitmap.createScaledBitmap(bitmap, 8, 8, true)
        if (scaled != bitmap) bitmap.recycle()
        val pixels = IntArray(64)
        scaled.getPixels(pixels, 0, 8, 0, 0, 8, 8)
        scaled.recycle()
        return IntArray(64) { i ->
            val p = pixels[i]
            val r = (p shr 16) and 0xFF
            val g = (p shr 8) and 0xFF
            val b = p and 0xFF
            (r * 299 + g * 587 + b * 114) / 1000
        }
    }

    /**
     * Variance of the Laplacian on a downscaled grayscale image. Lower variance means
     * a blurrier image. Returns null if undecodable.
     */
    fun laplacianVariance(context: Context, uri: Uri, side: Int = 100): Double? {
        val bitmap = decodeSampled(context, uri, side) ?: return null
        val scaled = Bitmap.createScaledBitmap(bitmap, side, side, true)
        if (scaled != bitmap) bitmap.recycle()
        val gray = IntArray(side * side)
        val px = IntArray(side * side)
        scaled.getPixels(px, 0, side, 0, 0, side, side)
        scaled.recycle()
        for (i in px.indices) {
            val p = px[i]
            gray[i] = (((p shr 16) and 0xFF) * 299 + ((p shr 8) and 0xFF) * 587 + (p and 0xFF) * 114) / 1000
        }
        var sum = 0.0
        var sumSq = 0.0
        var count = 0
        for (y in 1 until side - 1) {
            for (x in 1 until side - 1) {
                val idx = y * side + x
                val lap = (gray[idx - 1] + gray[idx + 1] + gray[idx - side] + gray[idx + side] -
                    4 * gray[idx]).toDouble()
                sum += lap
                sumSq += lap * lap
                count++
            }
        }
        if (count == 0) return null
        val mean = sum / count
        return sumSq / count - mean * mean
    }

    private fun decodeSampled(context: Context, uri: Uri, target: Int): Bitmap? = runCatching {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, bounds)
        }
        val (w, h) = bounds.outWidth to bounds.outHeight
        if (w <= 0 || h <= 0) return null
        var sample = 1
        while (w / (sample * 2) >= target && h / (sample * 2) >= target) sample *= 2
        val opts = BitmapFactory.Options().apply { inSampleSize = sample }
        context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, opts)
        }
    }.getOrNull()
}
