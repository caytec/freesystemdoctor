package com.freeandroiddoctor.android

import com.freeandroiddoctor.android.ai.DeviceHealthSnapshot
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceHealthSnapshotTest {

    private fun sample() = DeviceHealthSnapshot(
        storageTotalBytes = 128L * 1024 * 1024 * 1024,
        storageFreeBytes = 12L * 1024 * 1024 * 1024,
        ramTotalBytes = 8L * 1024 * 1024 * 1024,
        ramAvailableBytes = 2L * 1024 * 1024 * 1024,
        batteryPercent = 73,
        batteryTemperatureCelsius = 31.5f,
        reclaimableJunkBytes = 512L * 1024 * 1024,
        largestApps = listOf("Gallery" to 3L * 1024 * 1024 * 1024),
        locale = "pl",
    )

    @Test
    fun promptContainsKeyMetrics() {
        val text = sample().toPromptText()
        assertTrue(text.contains("Storage"))
        assertTrue(text.contains("RAM"))
        assertTrue(text.contains("Battery"))
        assertTrue(text.contains("73%"))
        assertTrue(text.contains("Gallery"))
    }

    @Test
    fun promptIsNonEmpty() {
        assertTrue(sample().toPromptText().isNotBlank())
    }
}
