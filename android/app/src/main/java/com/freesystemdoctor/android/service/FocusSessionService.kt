package com.freesystemdoctor.android.service

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
import com.freesystemdoctor.android.MainActivity
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Owns one Focus session: frees background RAM at start, switches the system to
 * Do-Not-Disturb (priority), and keeps an ongoing notification with an "End session"
 * action. Stops itself when the action fires or when the host process is killed.
 *
 * Honest behavior: we never silently mute emergency / starred-contact channels, because
 * we use `INTERRUPTION_FILTER_PRIORITY` (not `_NONE`). This matches what users actually
 * want from "focus" and avoids missed-call disasters.
 */
class FocusSessionService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var tick: Job? = null
    private var startedAt: Long = 0L
    private var previousFilter: Int = NotificationManager.INTERRUPTION_FILTER_ALL

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_END -> { stop(); return START_NOT_STICKY }
            else -> {
                if (startedAt != 0L) return START_STICKY
                startedAt = System.currentTimeMillis()
                ensureChannel(this)
                startForegroundCompat(buildNotification())
                scope.launch { ServiceLocator.memoryEngine.freeBackground() }
                previousFilter = ServiceLocator.focusEngine.enterDnd()
                tick?.cancel()
                tick = scope.launch {
                    while (isActive) {
                        delay(60_000)
                        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                        nm.notify(NOTIFICATION_ID, buildNotification())
                    }
                }
            }
        }
        return START_STICKY
    }

    private fun stop() {
        tick?.cancel()
        runCatching { ServiceLocator.focusEngine.restoreDnd(previousFilter) }
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        tick?.cancel()
        runCatching { ServiceLocator.focusEngine.restoreDnd(previousFilter) }
        super.onDestroy()
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

    private fun buildNotification(): Notification {
        val openIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val endIntent = PendingIntent.getService(
            this, 1,
            Intent(this, FocusSessionService::class.java).apply { action = ACTION_END },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val startedAtText = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(startedAt))
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(getString(R.string.focus_running_title))
            .setContentText(getString(R.string.focus_running_text, startedAtText))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openIntent)
            .addAction(0, getString(R.string.focus_end), endIntent)
            .build()
    }

    companion object {
        const val CHANNEL_ID = "fsd_focus"
        const val ACTION_END = "com.freesystemdoctor.android.action.FOCUS_END"
        private const val NOTIFICATION_ID = 4501

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.focus_channel),
                        NotificationManager.IMPORTANCE_LOW,
                    ),
                )
            }
        }

        fun start(context: Context) {
            ensureChannel(context)
            val intent = Intent(context, FocusSessionService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.startService(
                Intent(context, FocusSessionService::class.java).apply { action = ACTION_END },
            )
        }
    }
}
