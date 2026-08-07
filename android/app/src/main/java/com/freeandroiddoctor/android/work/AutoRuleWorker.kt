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
import com.freeandroiddoctor.android.data.automation.AutoRuleTrigger
import com.freeandroiddoctor.android.engine.automation.AutoRuleFiring
import java.util.Calendar
import java.util.concurrent.atomic.AtomicInteger

/**
 * Periodic worker that ticks every ~30 minutes and evaluates time / storage-based
 * auto-rules. Event-based rules (boot, app installed, charging-full) are dispatched
 * directly by their receivers and don't need this worker.
 */
class AutoRuleWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val engine = ServiceLocator.autoRulesEngine
        val firings = engine.evaluate(AutoRuleTrigger.LOW_STORAGE)

        val cal = Calendar.getInstance()
        if (cal.get(Calendar.DAY_OF_WEEK) == Calendar.SUNDAY && cal.get(Calendar.HOUR_OF_DAY) in 8..10) {
            firings.toMutableList().addAll(engine.evaluate(AutoRuleTrigger.WEEKLY_DEEP_SCAN))
        }

        firings.forEach { notify(applicationContext, it) }
        return Result.success()
    }

    companion object {
        const val CHANNEL_ID = "fsd_auto_rules"
        private val NEXT_NOTIFICATION_ID = AtomicInteger(5500)

        fun notify(context: Context, firing: AutoRuleFiring) {
            ensureChannel(context)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) return

            val notification = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentTitle(firing.title)
                .setContentText(firing.body)
                .setAutoCancel(true)
                .build()
            runCatching {
                NotificationManagerCompat.from(context).notify(NEXT_NOTIFICATION_ID.incrementAndGet(), notification)
            }
        }

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.auto_rules_channel),
                        NotificationManager.IMPORTANCE_LOW,
                    ),
                )
            }
        }
    }
}
