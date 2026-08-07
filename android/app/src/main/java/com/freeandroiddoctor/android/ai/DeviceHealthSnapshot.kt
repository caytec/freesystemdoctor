package com.freeandroiddoctor.android.ai

import com.freeandroiddoctor.android.core.util.ByteFormatter

/** Compact, local-only summary of device state handed to the AI for analysis. */
data class DeviceHealthSnapshot(
    val storageTotalBytes: Long,
    val storageFreeBytes: Long,
    val ramTotalBytes: Long,
    val ramAvailableBytes: Long,
    val batteryPercent: Int,
    val batteryTemperatureCelsius: Float,
    val reclaimableJunkBytes: Long,
    val largestApps: List<Pair<String, Long>>,
    val locale: String,
) {
    fun toPromptText(): String = buildString {
        appendLine("Storage: ${ByteFormatter.format(storageFreeBytes)} free of ${ByteFormatter.format(storageTotalBytes)}")
        appendLine("RAM: ${ByteFormatter.format(ramAvailableBytes)} free of ${ByteFormatter.format(ramTotalBytes)}")
        appendLine("Battery: $batteryPercent%, ${batteryTemperatureCelsius}°C")
        appendLine("Reclaimable junk: ${ByteFormatter.format(reclaimableJunkBytes)}")
        if (largestApps.isNotEmpty()) {
            appendLine("Largest apps:")
            largestApps.take(5).forEach { (name, bytes) ->
                appendLine("  - $name: ${ByteFormatter.format(bytes)}")
            }
        }
    }
}
