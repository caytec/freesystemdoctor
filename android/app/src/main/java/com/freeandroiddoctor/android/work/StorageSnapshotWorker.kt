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
import com.freeandroiddoctor.android.engine.forecast.ForecastResult
import kotlinx.coroutines.flow.first
import java.util.concurrent.TimeUnit

/**
 * Records a daily free-storage snapshot and (when the forecast crosses the warning threshold)
 * posts a non-intrusive notification. The notification is debounced to once per 72h to avoid
 * nagging the user during a slow refill cycle.
 */
class StorageSnapshotWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val engine = ServiceLocator.storageForecastEngine
        engine.recordToday()
        val report = engine.forecast()
        maybeWarn(report)
        return Result.success()
    }

    private suspend fun maybeWarn(report: ForecastResult) {
        if (report.state != ForecastResult.State.COUNTDOWN) return
        val days = report.daysUntilFull ?: return
        if (days >= WARN_THRESHOLD_DAYS) return

        val proStore = ServiceLocator.proStore
        val lastWarn = proStore.lastForecastWarnAt.first()
        val now = System.currentTimeMillis()
        if (now - lastWarn < TimeUnit.HOURS.toMillis(WARN_DEBOUNCE_HOURS.toLong())) return
        proStore.setLastForecastWarnAt(now)

        val ctx = applicationContext
        ensureChannel(ctx)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) return

        val notification = NotificationCompat.Builder(ctx, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(ctx.getString(R.string.storage_forecast_warn_title))
            .setContentText(ctx.getString(R.string.storage_forecast_warn_text, days.toInt()))
            .setAutoCancel(true)
            .build()
        runCatching { NotificationManagerCompat.from(ctx).notify(NOTIFICATION_ID, notification) }
    }

    companion object {
        const val CHANNEL_ID = "fsd_storage_forecast"
        private const val NOTIFICATION_ID = 4401
        const val WARN_THRESHOLD_DAYS = 14L
        const val WARN_DEBOUNCE_HOURS = 72

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.storage_forecast_channel),
                        NotificationManager.IMPORTANCE_LOW,
                    ),
                )
            }
        }
    }
}
