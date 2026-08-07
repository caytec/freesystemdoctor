package com.freeandroiddoctor.android.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.freeandroiddoctor.android.MainActivity
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.battery.ChargingSession
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.abs

/**
 * Samples the battery while plugged in, integrates `current_now` over time to estimate
 * mAh added, and writes one [ChargingSession] when the user unplugs (or when the service
 * is stopped). Triggered by [PowerEventReceiver] on `ACTION_POWER_CONNECTED`.
 *
 * Honest behavior: samples where |current| exceeds 8 A are rejected (OEM noise); when
 * the engine cannot read current at all the session is still recorded with `estMahAdded = 0`
 * so the UI can show "no current data" rather than fabricating a number.
 */
class ChargingSessionService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var sampler: Job? = null
    private var startTs: Long = 0L
    private var fromPct: Int = -1
    private var peakTempC: Float = Float.MIN_VALUE
    private val currentSamples = ArrayList<Int>()
    private var lastSampleTs: Long = 0L
    private var mahIntegral: Double = 0.0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> { finishAndStop(); return START_NOT_STICKY }
            else -> if (startTs == 0L) start()
        }
        return START_STICKY
    }

    private fun start() {
        ensureChannel(this)
        startForegroundCompat(buildNotification())
        startTs = System.currentTimeMillis()
        lastSampleTs = startTs
        val battery = ServiceLocator.batteryEngine.read()
        fromPct = battery.levelPercent
        peakTempC = battery.temperatureCelsius
        sampler?.cancel()
        sampler = scope.launch {
            while (isActive) {
                delay(SAMPLE_INTERVAL_MS)
                sampleOnce()
            }
        }
    }

    private fun sampleOnce() {
        val info = runCatching { ServiceLocator.batteryEngine.read() }.getOrNull() ?: return
        if (!info.isCharging) {
            finishAndStop()
            return
        }
        if (info.temperatureCelsius > peakTempC) peakTempC = info.temperatureCelsius
        info.currentNowMa?.let { ma ->
            if (abs(ma) <= MAX_CURRENT_MA) {
                currentSamples += ma
                val now = System.currentTimeMillis()
                val dtSec = ((now - lastSampleTs).coerceAtLeast(0L)) / 1000.0
                mahIntegral += abs(ma) * dtSec / 3600.0
                lastSampleTs = now
            }
        }
    }

    private fun finishAndStop() {
        sampler?.cancel()
        val endTs = System.currentTimeMillis()
        val toPct = runCatching { ServiceLocator.batteryEngine.read().levelPercent }.getOrDefault(fromPct)
        if (startTs != 0L && fromPct in 0..100 && toPct > fromPct) {
            val session = ChargingSession(
                startTs = startTs,
                endTs = endTs,
                fromPct = fromPct,
                toPct = toPct,
                peakTempC = peakTempC,
                avgCurrentMa = if (currentSamples.isEmpty()) 0 else currentSamples.average().toInt(),
                estMahAdded = mahIntegral.toInt(),
            )
            // NonCancellable: the write must survive scope.cancel() in onDestroy,
            // which fires right after stopSelf().
            scope.launch {
                withContext(NonCancellable) {
                    ServiceLocator.chargingSessionEngine.append(session)
                }
            }
        }
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        sampler?.cancel()
        scope.cancel()
        super.onDestroy()
    }

    private fun startForegroundCompat(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC,
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun buildNotification(): Notification {
        val openIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(getString(R.string.tool_charging_log))
            .setContentText(getString(R.string.charging_log_note))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openIntent)
            .build()
    }

    companion object {
        const val CHANNEL_ID = "fsd_charging"
        const val ACTION_STOP = "com.freeandroiddoctor.android.action.CHARGING_STOP"
        private const val NOTIFICATION_ID = 4502
        private const val SAMPLE_INTERVAL_MS = 30_000L
        private const val MAX_CURRENT_MA = 8000

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.tool_charging_log),
                        NotificationManager.IMPORTANCE_LOW,
                    ),
                )
            }
        }

        fun start(context: Context) {
            ensureChannel(context)
            val intent = Intent(context, ChargingSessionService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.startService(
                Intent(context, ChargingSessionService::class.java).apply { action = ACTION_STOP },
            )
        }
    }
}
