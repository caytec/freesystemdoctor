package com.freeandroiddoctor.android

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.freeandroiddoctor.android.engine.notifications.NotificationStatsEngine
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class NotificationStatsEngineTest {

    @Before
    fun clearState() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        File(ctx.filesDir, "notif_stats/stats.json").delete()
    }

    @Test
    fun recordsAndAggregates() = runBlocking {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val engine = NotificationStatsEngine(ctx)
        repeat(5) { engine.record("com.test.app") }
        repeat(2) { engine.record("com.other.app") }
        val top = engine.topApps()
        assertTrue(top.isNotEmpty())
        val testApp = top.first { it.packageName == "com.test.app" }
        assertTrue("Expected ≥5 counts", testApp.count >= 5)
    }

    @Test
    fun ignoresBlankPackageName() = runBlocking {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val engine = NotificationStatsEngine(ctx)
        engine.record("")
        engine.record("  ")
        val top = engine.topApps()
        assertTrue(top.none { it.packageName.isBlank() })
    }
}
