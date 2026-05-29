package com.freesystemdoctor.android.service

import android.app.KeyguardManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.freesystemdoctor.android.MainActivity
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

/**
 * Polls foreground app transitions and launches [BiometricPromptActivity] when a
 * user-locked app comes forward. The poll loop is paused when the screen is off or the
 * keyguard is up — this is the main battery-saving trick, otherwise this service would
 * be a constant drain.
 *
 * Per-package auth state is kept in a static map with a 30 s TTL so users don't get
 * re-prompted on every home-screen bounce.
 *
 * Foreground-service type: `specialUse` — declared in manifest with subtype `app_lock`.
 * Play submission requires a justification line; that copy lives in the Play Console
 * listing, not in the source.
 */
class AppLockService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var loop: Job? = null
    private var lastEventTs: Long = 0L
    private val screenReceiver = ScreenStateReceiver()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        ensureChannel(this)
        registerReceiver(
            screenReceiver,
            IntentFilter().apply {
                addAction(Intent.ACTION_SCREEN_ON)
                addAction(Intent.ACTION_SCREEN_OFF)
                addAction(Intent.ACTION_USER_PRESENT)
            },
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForegroundCompat(buildNotification(lockedCount = 0))
        scope.launch {
            ServiceLocator.appLockEngine.lockedPackages.collectLatest { locked ->
                val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                nm.notify(NOTIFICATION_ID, buildNotification(locked.size))
                if (locked.isEmpty()) {
                    loop?.cancel(); loop = null
                } else if (loop == null || loop?.isActive == false) {
                    startPolling()
                }
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        loop?.cancel()
        runCatching { unregisterReceiver(screenReceiver) }
        super.onDestroy()
    }

    private fun startPolling() {
        loop?.cancel()
        loop = scope.launch {
            val usm = getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            lastEventTs = System.currentTimeMillis() - TimeUnit.SECONDS.toMillis(2)
            while (isActive) {
                if (!screenActive()) {
                    delay(POLL_MS_IDLE)
                    continue
                }
                val now = System.currentTimeMillis()
                val events = usm.queryEvents(lastEventTs, now)
                val ev = UsageEvents.Event()
                while (events.hasNextEvent()) {
                    events.getNextEvent(ev)
                    if (ev.eventType == UsageEvents.Event.MOVE_TO_FOREGROUND) {
                        handleForeground(ev.packageName)
                    }
                }
                lastEventTs = now
                delay(POLL_MS_ACTIVE)
            }
        }
    }

    private suspend fun handleForeground(pkg: String) {
        if (pkg == packageName) return
        val locked = ServiceLocator.appLockEngine.lockedOnce()
        if (pkg !in locked) return
        val auth = authenticated[pkg] ?: 0L
        if (System.currentTimeMillis() - auth < AUTH_TTL_MS) return
        startActivity(BiometricPromptActivity.launchIntent(this, pkg))
    }

    private fun screenActive(): Boolean {
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        val km = getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
        return pm.isInteractive && !km.isKeyguardLocked
    }

    private fun startForegroundCompat(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE,
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun buildNotification(lockedCount: Int): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(getString(R.string.app_lock_running_title))
            .setContentText(getString(R.string.app_lock_running_text, lockedCount))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(open)
            .build()
    }

    private inner class ScreenStateReceiver : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                Intent.ACTION_SCREEN_OFF -> { loop?.cancel(); loop = null }
                Intent.ACTION_USER_PRESENT, Intent.ACTION_SCREEN_ON -> {
                    if (loop == null || loop?.isActive == false) startPolling()
                }
            }
        }
    }

    companion object {
        const val CHANNEL_ID = "fsd_app_lock"
        private const val NOTIFICATION_ID = 4601
        private const val POLL_MS_ACTIVE = 1500L
        private const val POLL_MS_IDLE = 5000L
        private val AUTH_TTL_MS = TimeUnit.SECONDS.toMillis(30)

        // Per-package auth grants visible to BiometricPromptActivity.
        private val authenticated = mutableMapOf<String, Long>()
        @Synchronized
        fun markAuthenticated(pkg: String) {
            authenticated[pkg] = System.currentTimeMillis()
        }

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.app_lock_channel),
                        NotificationManager.IMPORTANCE_LOW,
                    ),
                )
            }
        }

        fun start(context: Context) {
            ensureChannel(context)
            val intent = Intent(context, AppLockService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, AppLockService::class.java))
        }
    }
}
