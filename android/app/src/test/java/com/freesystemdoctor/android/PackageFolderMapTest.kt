package com.freesystemdoctor.android

import com.freesystemdoctor.android.engine.corpse.PackageFolderMap
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PackageFolderMapTest {

    @Test
    fun lookupMatchesCaseInsensitive() {
        val hit = PackageFolderMap.lookup("whatsapp")
        assertNotNull(hit)
        assertEquals("com.whatsapp", hit!!.packageName)
    }

    @Test
    fun lookupReturnsNullForUnknown() {
        assertNull(PackageFolderMap.lookup("not-a-real-folder"))
    }

    @Test
    fun noDuplicateFolderNames() {
        val names = PackageFolderMap.entries.map { it.folderName.lowercase() }
        assertEquals(names.size, names.toSet().size)
    }

    @Test
    fun packageNamesLookLikePackages() {
        PackageFolderMap.entries.forEach { entry ->
            assertTrue(
                "Bad package: ${entry.packageName}",
                entry.packageName.contains('.') && entry.packageName.length > 3,
            )
        }
    }
}
