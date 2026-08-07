package com.freeandroiddoctor.android.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.freeandroiddoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** Records every fully-removed package so CorpseFinder can flag fresh corpses HIGH risk. */
class UninstallWatcherReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_PACKAGE_FULLY_REMOVED) return
        val pkg = intent.data?.schemeSpecificPart ?: return
        val pending = goAsync()
        CoroutineScope(Dispatchers.Default).launch {
            try {
                ServiceLocator.corpseFinderEngine.appendUninstalled(pkg)
            } finally {
                pending.finish()
            }
        }
    }
}
