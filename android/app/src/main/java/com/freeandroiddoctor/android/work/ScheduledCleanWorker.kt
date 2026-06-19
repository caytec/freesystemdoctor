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
import com.freeandroiddoctor.android.core.util.ByteFormatter

/**
 * Periodic maintenance: clears the app's own cache (always safe, no consent needed)
 * and re-scans for reclaimable junk, then notifies the user. Shared-storage files are
 * never deleted silently — the notification invites the user to open the cleaner.
 */
class ScheduledCleanWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val junk = ServiceLocator.junkEngine
        val freed = runCatching { junk.cleanAppCache().bytesFreed }.getOrDefault(0L)
        val reclaimable = runCatching { junk.scan().reclaimableBytes }.getOrDefault(0L)
        notify(freed, reclaimable)
        return Result.success()
    }

    private fun notify(freedBytes: Long, reclaimableBytes: Long) {
        val ctx = applicationContext
        ensureChannel(ctx)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        val text = ctx.getString(
            R.string.work_clean_done,
            ByteFormatter.format(freedBytes),
            ByteFormatter.format(reclaimableBytes),
        )
        val notification = NotificationCompat.Builder(ctx, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(ctx.getString(R.string.work_clean_title))
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .build()
        runCatching { NotificationManagerCompat.from(ctx).notify(NOTIFICATION_ID, notification) }
    }

    companion object {
        const val CHANNEL_ID = "fsd_maintenance"
        private const val NOTIFICATION_ID = 4201

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.work_channel_name),
                        NotificationManager.IMPORTANCE_LOW,
                    ),
                )
            }
        }
    }
}
