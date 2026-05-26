package com.freesystemdoctor.android.work

import android.content.Context
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

    private companion object {
        const val UNIQUE_NAME = "fsd_scheduled_clean"
    }
}
