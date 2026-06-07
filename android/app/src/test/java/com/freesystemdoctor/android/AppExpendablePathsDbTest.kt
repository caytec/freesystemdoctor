package com.freesystemdoctor.android

import com.freesystemdoctor.android.engine.appdeep.AppExpendablePathsDb
import com.freesystemdoctor.android.engine.appdeep.Safety
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AppExpendablePathsDbTest {

    @Test
    fun rulesHaveNoEmptyPaths() {
        AppExpendablePathsDb.rules.forEach { rule ->
            assertFalse("Empty path for ${rule.packageName}", rule.relPath.isBlank())
            assertFalse("Empty label for ${rule.packageName}", rule.label.isBlank())
        }
    }

    @Test
    fun byPackageGroupsCorrectly() {
        val whatsappRules = AppExpendablePathsDb.byPackage["com.whatsapp"].orEmpty()
        assertTrue("Expected several WhatsApp rules", whatsappRules.size >= 3)
    }

    @Test
    fun optInRulesExistForRiskyPaths() {
        // Status backups should be OPT_IN, not SAFE — they're user-visible media.
        val statuses = AppExpendablePathsDb.rules.first {
            it.packageName == "com.whatsapp" && it.relPath.endsWith(".Statuses")
        }
        assertEquals(Safety.OPT_IN, statuses.safety)
    }
}
