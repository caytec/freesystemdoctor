package com.freeandroiddoctor.android

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.freeandroiddoctor.android.engine.battery.BatteryEngine
import com.freeandroiddoctor.android.engine.battery.BatteryHealthEngine
import com.freeandroiddoctor.android.engine.battery.ChargingSession
import com.freeandroiddoctor.android.engine.battery.ChargingSessionEngine
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class BatteryHealthEngineTest {

    @Before
    fun clearState() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        File(ctx.filesDir, "battery/sessions.json").delete()
    }

    @Test
    fun reportsNullWhenTooFewSamples() = runBlocking {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val sessions = ChargingSessionEngine(ctx)
        val now = System.currentTimeMillis()
        sessions.append(ChargingSession(now, now + 1, 10, 20, 30f, 0, 200)) // <40% delta
        val engine = BatteryHealthEngine(sessions, BatteryEngine(ctx))
        val r = engine.compute()
        assertNull(r.measuredCapacityMah)
        assertNull(r.healthPercent)
    }

    @Test
    fun reportsHealthWhenEnoughQualifyingSessions() = runBlocking {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val sessions = ChargingSessionEngine(ctx)
        val now = System.currentTimeMillis()
        repeat(3) { i ->
            sessions.append(
                ChargingSession(
                    startTs = now + i,
                    endTs = now + 1000 + i,
                    fromPct = 10,
                    toPct = 60,
                    peakTempC = 30f,
                    avgCurrentMa = 1000,
                    estMahAdded = 2000,
                ),
            )
        }
        val engine = BatteryHealthEngine(sessions, BatteryEngine(ctx))
        val r = engine.compute()
        assertNotNull(r.measuredCapacityMah)
        // estMahAdded / (delta/100) = 2000 / 0.5 = 4000 mAh
        assertEquals(4000, r.measuredCapacityMah)
    }
}
