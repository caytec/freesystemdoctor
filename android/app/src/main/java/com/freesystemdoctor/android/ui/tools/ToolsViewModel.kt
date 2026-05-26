package com.freesystemdoctor.android.ui.tools

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn

class ToolsViewModel : ViewModel() {

    private val billing = ServiceLocator.billingManager
    private val proStore = ServiceLocator.proStore

    /** Advanced tools unlock when the user is Pro or has an active rewarded-ad unlock. */
    val advancedUnlocked: StateFlow<Boolean> =
        combine(billing.isPro, proStore.rewardUntil) { pro, until ->
            pro || until > System.currentTimeMillis()
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)
}
