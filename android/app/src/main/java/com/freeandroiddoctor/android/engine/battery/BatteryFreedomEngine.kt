package com.freeandroiddoctor.android.engine.battery

import android.content.Context
import android.content.pm.ApplicationInfo
import android.os.PowerManager
import android.os.SystemClock
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlin.coroutines.coroutineContext

/** An app that the OS is NOT allowed to put to sleep. */
data class UnrestrictedApp(
    val packageName: String,
    val label: String,
)

data class BatteryFreedomReport(
    val unrestricted: List<UnrestrictedApp>,
    val scannedApps: Int,
    /** Share of time since boot the CPU stayed awake (0..1); lower is better. */
    val awakeFraction: Float,
    val deepSleepMillis: Long,
    val uptimeMillis: Long,
)

/**
 * The honest version of "hibernation" / "sleep mode".
 *
 * Competitors sell a button that kills processes — which Android immediately restarts, so
 * it changes nothing. What actually governs background drain is whether an app is exempt
 * from Doze / App Standby, and that is readable for any package via the public
 * [PowerManager.isIgnoringBatteryOptimizations]. We list the exempt apps and deep-link the
 * user to the system screen where the exemption can genuinely be revoked.
 *
 * Deep-sleep ratio comes from the difference between [SystemClock.elapsedRealtime] (counts
 * time in suspend) and [SystemClock.uptimeMillis] (does not) — the one battery number that
 * actually predicts overnight drain.
 *
 * Deliberately NOT implemented: per-app wakelock attribution and App Standby buckets for
 * other packages. Both need `dumpsys` / a hidden `@SystemApi`, i.e. ADB or Shizuku — so we
 * don't fake them.
 */
class BatteryFreedomEngine(private val context: Context) {

    suspend fun scan(): BatteryFreedomReport = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val power = context.getSystemService(Context.POWER_SERVICE) as PowerManager

        val apps = runCatching { pm.getInstalledApplications(0) }
            .getOrDefault(emptyList())
            .filter { (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 }
            .filter { it.packageName != context.packageName }

        val unrestricted = ArrayList<UnrestrictedApp>()
        apps.forEach { app ->
            coroutineContext.ensureActive()
            val exempt = runCatching {
                power.isIgnoringBatteryOptimizations(app.packageName)
            }.getOrDefault(false)
            if (exempt) {
                unrestricted += UnrestrictedApp(
                    packageName = app.packageName,
                    label = runCatching { pm.getApplicationLabel(app).toString() }
                        .getOrDefault(app.packageName),
                )
            }
        }

        val elapsed = SystemClock.elapsedRealtime()
        val awake = SystemClock.uptimeMillis()
        val deepSleep = (elapsed - awake).coerceAtLeast(0L)

        BatteryFreedomReport(
            unrestricted = unrestricted.sortedBy { it.label.lowercase() },
            scannedApps = apps.size,
            awakeFraction = if (elapsed <= 0) 0f else (awake.toFloat() / elapsed).coerceIn(0f, 1f),
            deepSleepMillis = deepSleep,
            uptimeMillis = elapsed,
        )
    }
}
