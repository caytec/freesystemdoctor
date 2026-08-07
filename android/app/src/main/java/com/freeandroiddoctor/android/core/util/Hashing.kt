package com.freeandroiddoctor.android.core.util

import java.io.InputStream
import java.security.MessageDigest

/** Hashing helpers for duplicate detection. */
object Hashing {

    private const val BUFFER_SIZE = 64 * 1024

    /** Streaming SHA-256 of an arbitrary input stream, returned as lowercase hex. */
    fun sha256(input: InputStream): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(BUFFER_SIZE)
        input.use { stream ->
            var read = stream.read(buffer)
            while (read >= 0) {
                digest.update(buffer, 0, read)
                read = stream.read(buffer)
            }
        }
        return digest.digest().toHex()
    }

    /**
     * 64-bit average-hash (aHash) of a grayscale 8x8 sample, used for "similar image"
     * grouping. [pixels] must contain exactly 64 luminance values (0..255).
     */
    fun averageHash(pixels: IntArray): Long {
        require(pixels.size == 64) { "averageHash expects 64 samples" }
        val mean = pixels.sum() / 64.0
        var hash = 0L
        for (i in pixels.indices) {
            if (pixels[i] >= mean) {
                hash = hash or (1L shl i)
            }
        }
        return hash
    }

    /** Hamming distance between two perceptual hashes (0 == identical). */
    fun hammingDistance(a: Long, b: Long): Int = java.lang.Long.bitCount(a xor b)

    private fun ByteArray.toHex(): String {
        val sb = StringBuilder(size * 2)
        for (b in this) {
            val v = b.toInt() and 0xFF
            sb.append(Character.forDigit(v ushr 4, 16))
            sb.append(Character.forDigit(v and 0x0F, 16))
        }
        return sb.toString()
    }
}
