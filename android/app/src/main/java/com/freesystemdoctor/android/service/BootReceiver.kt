package com.freesystemdoctor.android.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.freesystemdoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/** Restarts the monitor notification after reboot if the user enabled it. */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val pending = goAsync()
        CoroutineScope(Dispatchers.Default).launch {
            try {
                val enabled = ServiceLocator.settingsRepository.settings.first().monitorEnabled
                if (enabled) MonitorService.start(context.applicationContext)
            } finally {
                pending.finish()
            }
        }
    }
}
