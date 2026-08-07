package com.freeandroiddoctor.android.ui.tools

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class ToolsViewModel : ViewModel() {

    private val billing = ServiceLocator.billingManager
    private val proStore = ServiceLocator.proStore

    /**
     * Global Pro unlock: real entitlement, legacy 24h advanced reward, or active 3-day trial.
     * Per-tool 24h unlocks live in [unlocks] and are checked separately via [isUnlocked].
     */
    val advancedUnlocked: StateFlow<Boolean> =
        combine(billing.isPro, proStore.rewardUntil, proStore.trialUntil) { pro, reward, trial ->
            val now = System.currentTimeMillis()
            pro || reward > now || trial > now
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)

    /** Per-tool unlocks granted via rewarded ad, keyed by nav route. Pruned by [ProStore]. */
    val unlocks: StateFlow<Map<String, Long>> =
        proStore.toolUnlocks.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyMap())

    /** Has the user already burned their one-time 3-day trial? */
    val trialUsed: StateFlow<Boolean> =
        proStore.trialUsed.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)

    /**
     * True when the trial recently expired and we haven't shown the "trial ended" sheet yet.
     * Drives a one-time soft notice at the next locked-tool tap (anti-paywall-ambush per
     * Play UX policy).
     */
    val trialJustExpired: StateFlow<Boolean> =
        combine(
            proStore.trialUntil,
            proStore.trialUsed,
            proStore.trialExpiryNoticeShown,
            billing.isPro,
        ) { until, used, shown, pro ->
            !pro && used && until in 1L..System.currentTimeMillis() && !shown
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)

    /** Is [route] currently unlocked (Pro, trial, legacy reward, or per-tool unlock)? */
    fun isUnlocked(route: String): Boolean {
        if (advancedUnlocked.value) return true
        val expiry = unlocks.value[route] ?: return false
        return expiry > System.currentTimeMillis()
    }

    fun markTrialExpiryNoticeShown() {
        viewModelScope.launch { proStore.markTrialExpiryNoticeShown() }
    }
}
