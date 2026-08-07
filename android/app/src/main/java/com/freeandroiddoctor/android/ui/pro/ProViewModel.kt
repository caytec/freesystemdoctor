package com.freeandroiddoctor.android.ui.pro

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.billing.BillingManager
import com.freeandroiddoctor.android.billing.ProProduct
import com.freeandroiddoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

class ProViewModel : ViewModel() {

    private val billing: BillingManager = ServiceLocator.billingManager
    private val ads = ServiceLocator.adsController
    private val proStore = ServiceLocator.proStore

    val products: StateFlow<List<ProProduct>> = billing.products
    val isPro: StateFlow<Boolean> = billing.isPro

    val trialUsed: StateFlow<Boolean> =
        proStore.trialUsed.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)

    val trialUntil: StateFlow<Long> =
        proStore.trialUntil.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0L)

    fun purchase(activity: Activity, product: ProProduct) = billing.purchase(activity, product)
    fun restore() = billing.restore()

    fun rewardedReady(): Boolean = ads.rewardedReady

    /** Legacy 24h global advanced unlock (kept for grandfathered installs). */
    fun watchAdToUnlock(activity: Activity, onGranted: () -> Unit) {
        ads.showRewarded(activity) {
            viewModelScope.launch {
                proStore.grantAdvancedReward(TimeUnit.HOURS.toMillis(24))
                onGranted()
            }
        }
    }

    /** Starts the one-time 3-day Pro trial after a rewarded ad completes. */
    fun watchAdForTrial(activity: Activity, onGranted: () -> Unit) {
        ads.showRewarded(activity) {
            viewModelScope.launch {
                proStore.grantTrial(TimeUnit.DAYS.toMillis(3))
                onGranted()
            }
        }
    }
}
