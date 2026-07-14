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
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

/**
 * Owns one Game Boost session. On start it (1) frees background RAM, (2) purges this app's
 * own caches to give the game storage headroom, (3) optionally enters Do-Not-Disturb, (4)
 * suppresses our own interstitial / app-open ads, (5) optionally launches the chosen game.
 * Stops itself when the "End boost" action fires or when the host process is killed.
 *
 * Honest behaviour: every measurement reported is real (RAM delta + cache bytes returned
 * by the engines). We do NOT raise CPU clocks, change the thermal mode, or claim FPS gains.
 *
 * Foreground-service type: `specialUse` — declared in manifest with subtype `game_boost`.
 */
class GameBoostService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var startedAt: Long = 0L
    private var previousDndFilter: Int = NotificationManager.INTERRUPTION_FILTER_ALL
    private var dndWasApplied: Boolean = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_END -> {
                stop()
                return START_NOT_STICKY
            }
            else -> {
                if (startedAt != 0L) return START_STICKY
                startedAt = System.currentTimeMillis()
                ensureChannel(this)
                startForegroundCompat(buildNotification())

                val enterDnd = intent?.getBooleanExtra(EXTRA_ENTER_DND, true) ?: true
                val launchPackage = intent?.getStringExtra(EXTRA_LAUNCH_PACKAGE)

                scope.launch {
                    runCatching { ServiceLocator.gameBoostEngine.runBoost() }
                    if (enterDnd && ServiceLocator.focusEngine.hasDndAccess()) {
                        previousDndFilter = ServiceLocator.focusEngine.enterDnd()
                        dndWasApplied = true
                    }
                    // Suppress our own ads for the duration of the session (capped at 2h).
                    runCatching {
                        ServiceLocator.appOpenAdManager.suppressForMillis(SUPPRESS_MS)
                    }
                    if (launchPackage != null) {
                        runCatching {
                            ServiceLocator.gameBoostEngine.launchIntent(launchPackage)
                                ?.let { startActivity(it) }
                        }
                    }
                }
            }
        }
        return START_STICKY
    }

    private fun stop() {
        if (dndWasApplied) {
            runCatching { ServiceLocator.focusEngine.restoreDnd(previousDndFilter) }
            dndWasApplied = false
        }
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        if (dndWasApplied) {
            runCatching { ServiceLocator.focusEngine.restoreDnd(previousDndFilter) }
        }
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
            Intent(this, GameBoostService::class.java).apply { action = ACTION_END },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(getString(R.string.game_boost_running_title))
            .setContentText(getString(R.string.game_boost_running_text))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openIntent)
            .addAction(0, getString(R.string.game_boost_end), endIntent)
            .build()
    }

    companion object {
        const val CHANNEL_ID = "fsd_game_boost"
        const val ACTION_END = "com.freeandroiddoctor.android.action.GAME_BOOST_END"
        const val EXTRA_ENTER_DND = "enter_dnd"
        const val EXTRA_LAUNCH_PACKAGE = "launch_package"
        private const val NOTIFICATION_ID = 4801
        private val SUPPRESS_MS = TimeUnit.HOURS.toMillis(2)

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.game_boost_channel),
                        NotificationManager.IMPORTANCE_LOW,
                    ),
                )
            }
        }

        fun start(context: Context, enterDnd: Boolean, launchPackage: String?) {
            ensureChannel(context)
            val intent = Intent(context, GameBoostService::class.java).apply {
                putExtra(EXTRA_ENTER_DND, enterDnd)
                if (launchPackage != null) putExtra(EXTRA_LAUNCH_PACKAGE, launchPackage)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.startService(
                Intent(context, GameBoostService::class.java).apply { action = ACTION_END },
            )
        }
    }
}
