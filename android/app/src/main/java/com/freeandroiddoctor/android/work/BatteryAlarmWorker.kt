package com.freeandroiddoctor.android.work

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.first

/**
 * Periodically samples the battery level and fires a notification when it crosses the
 * user-configured low or full threshold. Notifications use a separate channel so the
 * maintenance channel stays low-importance for the cleaner notification.
 */
class BatteryAlarmWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val ctx = applicationContext
        val settings = ServiceLocator.settingsRepository.settings.first()
        if (!settings.batteryAlarmsEnabled) return Result.success()
        val (percent, charging) = ServiceLocator.batteryEngine.snapshot()
        val low = settings.batteryAlarmLow
        val full = settings.batteryAlarmFull
        if (charging && percent >= full) {
            notify(NOTIFICATION_ID_FULL, ctx.getString(R.string.battery_alarm_full_title),
                ctx.getString(R.string.battery_alarm_full_text, percent))
        } else if (!charging && percent <= low) {
            notify(NOTIFICATION_ID_LOW, ctx.getString(R.string.battery_alarm_low_title),
                ctx.getString(R.string.battery_alarm_low_text, percent))
        }
        return Result.success()
    }

    private fun notify(id: Int, title: String, text: String) {
        val ctx = applicationContext
        ensureChannel(ctx)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) return
        val notification = NotificationCompat.Builder(ctx, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(text)
            .setAutoCancel(true)
            .build()
        runCatching { NotificationManagerCompat.from(ctx).notify(id, notification) }
    }

    companion object {
        const val CHANNEL_ID = "fsd_battery_alarms"
        private const val NOTIFICATION_ID_LOW = 4301
        private const val NOTIFICATION_ID_FULL = 4302

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.battery_alarm_channel),
                        NotificationManager.IMPORTANCE_DEFAULT,
                    ),
                )
            }
        }
    }
}
