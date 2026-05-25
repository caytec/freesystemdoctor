package com.freesystemdoctor.android

import com.freesystemdoctor.android.core.util.ByteFormatter
import org.junit.Assert.assertEquals
import org.junit.Test

class ByteFormatterTest {

    @Test
    fun formatsBytes() {
        assertEquals("512 B", ByteFormatter.format(512))
    }

    @Test
    fun formatsKilobytes() {
        assertEquals("1.0 KB", ByteFormatter.format(1024))
    }

    @Test
    fun formatsMegabytes() {
        assertEquals("1.5 MB", ByteFormatter.format(1_572_864))
    }

    @Test
    fun formatsGigabytes() {
        assertEquals("2.0 GB", ByteFormatter.format(2L * 1024 * 1024 * 1024))
    }

    @Test
    fun formatsZero() {
        assertEquals("0 B", ByteFormatter.format(0))
    }
}
