package com.freesystemdoctor.android.core.util

import java.util.Locale
import kotlin.math.abs

/** Formats a byte count into a human-readable string (binary units). */
object ByteFormatter {

    private val units = arrayOf("B", "KB", "MB", "GB", "TB", "PB")

    fun format(bytes: Long): String {
        if (bytes < 1024 && bytes > -1024) return "$bytes B"
        var value = bytes.toDouble()
        var unitIndex = 0
        while (abs(value) >= 1024 && unitIndex < units.size - 1) {
            value /= 1024.0
            unitIndex++
        }
        return String.format(Locale.US, "%.1f %s", value, units[unitIndex])
    }
}
