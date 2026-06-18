package com.freesystemdoctor.android.work

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class WorkScheduler(private val context: Context) {

    fun setScheduledCleaning(enabled: Boolean, intervalHours: Long = 24) {
        val wm = WorkManager.getInstance(context)
        if (enabled) {
            val request = PeriodicWorkRequestBuilder<ScheduledCleanWorker>(
                intervalHours.coerceAtLeast(1), TimeUnit.HOURS,
            ).build()
            wm.enqueueUniquePeriodicWork(
                UNIQUE_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request,
            )
        } else {
            wm.cancelUniqueWork(UNIQUE_NAME)
        }
    }

    fun setBatteryAlarms(enabled: Boolean) {
        val wm = WorkManager.getInstance(context)
        if (enabled) {
            val request = PeriodicWorkRequestBuilder<BatteryAlarmWorker>(
                15, TimeUnit.MINUTES,
            ).build()
            wm.enqueueUniquePeriodicWork(
                BATTERY_ALARM_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request,
            )
            BatteryAlarmWorker.ensureChannel(context)
        } else {
            wm.cancelUniqueWork(BATTERY_ALARM_NAME)
        }
    }

    fun setStorageSnapshots(enabled: Boolean) {
        val wm = WorkManager.getInstance(context)
        if (enabled) {
            val request = PeriodicWorkRequestBuilder<StorageSnapshotWorker>(1, TimeUnit.DAYS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiresBatteryNotLow(true)
                        .build(),
                )
                .build()
            wm.enqueueUniquePeriodicWork(
                STORAGE_SNAPSHOT_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request,
            )
            StorageSnapshotWorker.ensureChannel(context)
        } else {
            wm.cancelUniqueWork(STORAGE_SNAPSHOT_NAME)
        }
    }

    fun setAutoRules(enabled: Boolean) {
        val wm = WorkManager.getInstance(context)
        if (enabled) {
            val request = PeriodicWorkRequestBuilder<AutoRuleWorker>(30, TimeUnit.MINUTES)
                .setConstraints(Constraints.Builder().setRequiresBatteryNotLow(true).build())
                .build()
            wm.enqueueUniquePeriodicWork(
                AUTO_RULES_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request,
            )
            AutoRuleWorker.ensureChannel(context)
        } else {
            wm.cancelUniqueWork(AUTO_RULES_NAME)
        }
    }

    fun setCloudBackupSchedule(enabled: Boolean) {
        val wm = WorkManager.getInstance(context)
        if (enabled) {
            val request = PeriodicWorkRequestBuilder<CloudBackupWorker>(7, TimeUnit.DAYS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiresBatteryNotLow(true)
                        .setRequiresStorageNotLow(true)
                        .build(),
                )
                .build()
            wm.enqueueUniquePeriodicWork(
                CLOUD_BACKUP_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request,
            )
            CloudBackupWorker.ensureChannel(context)
        } else {
            wm.cancelUniqueWork(CLOUD_BACKUP_NAME)
        }
    }

    private companion object {
        const val UNIQUE_NAME = "fsd_scheduled_clean"
        const val BATTERY_ALARM_NAME = "fsd_battery_alarms"
        const val STORAGE_SNAPSHOT_NAME = "fsd_storage_snapshots"
        const val CLOUD_BACKUP_NAME = "fsd_cloud_backup"
        const val AUTO_RULES_NAME = "fsd_auto_rules"
    }
}
