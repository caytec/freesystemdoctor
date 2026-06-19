package com.freeandroiddoctor.android.ui.automation

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.data.automation.AutoRule
import com.freeandroiddoctor.android.data.automation.AutoRuleAction
import com.freeandroiddoctor.android.data.automation.AutoRuleTrigger
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.UUID

class AutoRulesViewModel(app: Application) : AndroidViewModel(app) {

    private val store = ServiceLocator.autoRuleStore
    private val scheduler = ServiceLocator.workScheduler

    val rules: StateFlow<List<AutoRule>> = store.rules
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun toggle(id: String, enabled: Boolean) {
        viewModelScope.launch {
            store.setEnabled(id, enabled)
            ensureScheduler()
        }
    }

    fun delete(id: String) {
        viewModelScope.launch {
            store.delete(id)
            ensureScheduler()
        }
    }

    fun addPreset(trigger: AutoRuleTrigger) {
        viewModelScope.launch {
            val rule = AutoRule(
                id = UUID.randomUUID().toString(),
                labelKey = when (trigger) {
                    AutoRuleTrigger.LOW_STORAGE -> "auto_rule_low_storage"
                    AutoRuleTrigger.CHARGING_FULL -> "auto_rule_charging"
                    AutoRuleTrigger.BOOT -> "auto_rule_boot"
                    AutoRuleTrigger.WEEKLY_DEEP_SCAN -> "auto_rule_weekly"
                    AutoRuleTrigger.OPEN_WIFI_DETECTED -> "auto_rule_open_wifi"
                    AutoRuleTrigger.APP_INSTALLED -> "auto_rule_install"
                },
                trigger = trigger,
                action = when (trigger) {
                    AutoRuleTrigger.LOW_STORAGE -> AutoRuleAction.NOTIFY_DEEP_SCAN
                    AutoRuleTrigger.CHARGING_FULL -> AutoRuleAction.RUN_CACHE_CLEAN
                    AutoRuleTrigger.BOOT -> AutoRuleAction.ACTIVATE_MODE
                    AutoRuleTrigger.WEEKLY_DEEP_SCAN -> AutoRuleAction.NOTIFY_DEEP_SCAN
                    AutoRuleTrigger.OPEN_WIFI_DETECTED -> AutoRuleAction.ACTIVATE_MODE
                    AutoRuleTrigger.APP_INSTALLED -> AutoRuleAction.NOTIFY_INSTALL_RISK
                },
                triggerThreshold = if (trigger == AutoRuleTrigger.LOW_STORAGE) 10 else 70,
                modeIdParam = when (trigger) {
                    AutoRuleTrigger.BOOT -> "focus"
                    AutoRuleTrigger.OPEN_WIFI_DETECTED -> "privacy"
                    else -> null
                },
                isPro = trigger == AutoRuleTrigger.APP_INSTALLED,
            )
            store.upsert(rule)
            ensureScheduler()
        }
    }

    private suspend fun ensureScheduler() {
        val any = store.enabledOnce().isNotEmpty()
        scheduler.setAutoRules(any)
    }
}
