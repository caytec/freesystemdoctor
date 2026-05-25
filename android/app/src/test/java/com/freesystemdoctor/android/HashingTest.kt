package com.freesystemdoctor.android

import com.freesystemdoctor.android.core.util.Hashing
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class HashingTest {

    @Test
    fun sha256MatchesKnownVector() {
        // SHA-256 of empty input.
        val hash = Hashing.sha256("".byteInputStream())
        assertEquals(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            hash,
        )
    }

    @Test
    fun sha256IsStableForSameContent() {
        val a = Hashing.sha256("freesystemdoctor".byteInputStream())
        val b = Hashing.sha256("freesystemdoctor".byteInputStream())
        assertEquals(a, b)
    }

    @Test
    fun sha256DiffersForDifferentContent() {
        val a = Hashing.sha256("a".byteInputStream())
        val b = Hashing.sha256("b".byteInputStream())
        assertNotEquals(a, b)
    }

    @Test
    fun averageHashIdenticalImagesHaveZeroDistance() {
        val pixels = IntArray(64) { it * 4 % 256 }
        val h1 = Hashing.averageHash(pixels)
        val h2 = Hashing.averageHash(pixels.copyOf())
        assertEquals(0, Hashing.hammingDistance(h1, h2))
    }

    @Test
    fun averageHashSimilarImagesHaveSmallDistance() {
        val base = IntArray(64) { if (it < 32) 10 else 200 }
        val tweaked = base.copyOf().also { it[0] = 250 }
        val distance = Hashing.hammingDistance(
            Hashing.averageHash(base),
            Hashing.averageHash(tweaked),
        )
        assertTrue("distance should be small, was $distance", distance <= 2)
    }
}
