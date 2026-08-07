package com.freeandroiddoctor.android

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.freeandroiddoctor.android.engine.battery.ChargingSession
import com.freeandroiddoctor.android.engine.battery.ChargingSessionEngine
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class ChargingSessionEngineTest {

    @Before
    fun clearState() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        File(ctx.filesDir, "battery/sessions.json").delete()
    }

    @Test
    fun appendAndRead() = runBlocking {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val engine = ChargingSessionEngine(ctx)
        val now = System.currentTimeMillis()
        val s = ChargingSession(
            startTs = now,
            endTs = now + 1_000_000L,
            fromPct = 20,
            toPct = 80,
            peakTempC = 32.5f,
            avgCurrentMa = 1200,
            estMahAdded = 2400,
        )
        engine.append(s)
        val sessions = engine.sessions()
        assertTrue("Expected at least one session", sessions.isNotEmpty())
        assertEquals(80, sessions.first().toPct)
    }

    @Test
    fun rejectsZeroDuration() = runBlocking {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val engine = ChargingSessionEngine(ctx)
        val before = engine.sessions().size
        engine.append(ChargingSession(0, 0, 10, 20, 30f, 0, 0))
        assertEquals(before, engine.sessions().size)
    }
}
