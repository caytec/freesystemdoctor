package com.freesystemdoctor.android.ui.pro

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.billing.BillingManager
import com.freesystemdoctor.android.billing.ProProduct
import com.freesystemdoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

class ProViewModel : ViewModel() {

    private val billing: BillingManager = ServiceLocator.billingManager
    private val ads = ServiceLocator.adsController
    private val proStore = ServiceLocator.proStore

    val products: StateFlow<List<ProProduct>> = billing.products
    val isPro: StateFlow<Boolean> = billing.isPro

    fun purchase(activity: Activity, product: ProProduct) = billing.purchase(activity, product)
    fun restore() = billing.restore()

    fun rewardedReady(): Boolean = ads.rewardedReady

    fun watchAdToUnlock(activity: Activity, onGranted: () -> Unit) {
        ads.showRewarded(activity) {
            viewModelScope.launch {
                proStore.grantAdvancedReward(TimeUnit.HOURS.toMillis(24))
                onGranted()
            }
        }
    }
}
