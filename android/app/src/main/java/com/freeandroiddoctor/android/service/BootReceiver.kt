package com.freeandroiddoctor.android.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.freeandroiddoctor.android.core.di.ServiceLocator
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
                runCatching { ServiceLocator.appModesEngine.reapplyOnBoot() }
                runCatching {
                    val rules = ServiceLocator.autoRuleStore.enabledOnce()
                    if (rules.isNotEmpty()) {
                        ServiceLocator.workScheduler.setAutoRules(true)
                        ServiceLocator.autoRulesEngine.evaluate(
                            com.freeandroiddoctor.android.data.automation.AutoRuleTrigger.BOOT,
                        )
                    }
                }
            } finally {
                pending.finish()
            }
        }
    }
}
