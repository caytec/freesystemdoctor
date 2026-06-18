package com.freesystemdoctor.android.analytics

/**
 * Thin analytics abstraction. The default [LogAnalytics] impl writes to Logcat and
 * compiles without any Firebase dependency. Swap for FirebaseAnalytics once
 * google-services.json is added to each product-flavor source set.
 */
interface Analytics {
    fun log(event: AnalyticsEvent)
}

sealed class AnalyticsEvent {
    /** User sees the paywall / unlock sheet. */
    data class PaywallView(val route: String, val source: String = "") : AnalyticsEvent()

    /** A Pro purchase (sub or lifetime) was acknowledged successfully. */
    data class PaywallPurchase(val sku: String) : AnalyticsEvent()

    /** Rewarded ad finished. */
    data class RewardedView(val granted: Boolean) : AnalyticsEvent()

    /** User exhausted a daily quota and the gate triggered. */
    data class QuotaExhausted(val key: String) : AnalyticsEvent()

    /** 3-day trial started via rewarded ad. */
    object TrialStart : AnalyticsEvent()

    /** Trial user made their first paid purchase. */
    object TrialConvert : AnalyticsEvent()
}
