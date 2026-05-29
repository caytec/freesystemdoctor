package com.freesystemdoctor.android.work

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.net.Uri
import android.os.Build
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.cloudbackup.BackupOptions
import kotlinx.coroutines.flow.first

/**
 * Weekly auto-backup. We deliberately keep the configuration minimal — the worker only
 * fires for users who have already picked a destination folder, set a passphrase
 * (kept encrypted at rest by EncryptedSharedPreferences) and toggled the schedule on.
 *
 * For v1 we DO NOT auto-include contacts/SMS in the scheduled backup (only settings +
 * app list). Sensitive content always requires the user to be present in the manual flow,
 * to satisfy Play user-data policy expectations.
 */
class CloudBackupWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val safStore = ServiceLocator.safTreeStore
        val tree = safStore.backupTreeUri.first() ?: return Result.success()
        val passphrase = ServiceLocator.cloudBackupKeyStore.read() ?: return Result.success()
        val settings = ServiceLocator.settingsRepository.settings.first()

        val engine = ServiceLocator.cloudBackupEngine
        runCatching {
            engine.runBackup(tree, passphrase.toCharArray(), BackupOptions(), settings)
            engine.rotateOlder(tree, keep = 5)
        }
        return Result.success()
    }

    companion object {
        const val CHANNEL_ID = "fsd_cloud_backup"

        fun ensureChannel(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        context.getString(R.string.cloud_backup_channel),
                        NotificationManager.IMPORTANCE_LOW,
                    ),
                )
            }
        }
    }
}
