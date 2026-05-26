package com.freesystemdoctor.android.ads

import android.app.Activity
import android.content.Context
import com.google.android.gms.ads.AdError
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.FullScreenContentCallback
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.MobileAds
import com.google.android.gms.ads.interstitial.InterstitialAd
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback
import com.google.android.gms.ads.rewarded.RewardedAd
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback

/**
 * Loads and shows AdMob interstitial and rewarded ads. Honours the Pro entitlement (no
 * ads for Pro), the UMP consent result, and a frequency cap so interstitials never feel
 * spammy — both Play-policy and UX requirements.
 */
class AdsController(private val appContext: Context) {

    @Volatile var canRequestAds: Boolean = false
        private set

    var proProvider: () -> Boolean = { false }

    private var initialized = false
    private var interstitial: InterstitialAd? = null
    private var rewarded: RewardedAd? = null
    private var lastInterstitialAt = 0L

    fun initialize(canRequest: Boolean) {
        canRequestAds = canRequest
        if (!canRequest) return
        if (!initialized) {
            MobileAds.initialize(appContext) {}
            initialized = true
        }
        preloadInterstitial()
        preloadRewarded()
    }

    private fun adsAllowed(): Boolean = canRequestAds && !proProvider()

    private fun preloadInterstitial() {
        if (!adsAllowed() || interstitial != null) return
        InterstitialAd.load(
            appContext,
            AdUnits.INTERSTITIAL,
            AdRequest.Builder().build(),
            object : InterstitialAdLoadCallback() {
                override fun onAdLoaded(ad: InterstitialAd) {
                    interstitial = ad
                }

                override fun onAdFailedToLoad(error: LoadAdError) {
                    interstitial = null
                }
            },
        )
    }

    /** Shows an interstitial if allowed and the frequency cap has elapsed. */
    fun maybeShowInterstitial(activity: Activity) {
        if (!adsAllowed()) return
        val ad = interstitial ?: run { preloadInterstitial(); return }
        if (System.currentTimeMillis() - lastInterstitialAt < MIN_INTERVAL_MS) return
        ad.fullScreenContentCallback = object : FullScreenContentCallback() {
            override fun onAdDismissedFullScreenContent() {
                interstitial = null
                preloadInterstitial()
            }

            override fun onAdFailedToShowFullScreenContent(error: AdError) {
                interstitial = null
                preloadInterstitial()
            }
        }
        lastInterstitialAt = System.currentTimeMillis()
        ad.show(activity)
    }

    private fun preloadRewarded() {
        if (!canRequestAds || rewarded != null) return
        RewardedAd.load(
            appContext,
            AdUnits.REWARDED,
            AdRequest.Builder().build(),
            object : RewardedAdLoadCallback() {
                override fun onAdLoaded(ad: RewardedAd) {
                    rewarded = ad
                }

                override fun onAdFailedToLoad(error: LoadAdError) {
                    rewarded = null
                }
            },
        )
    }

    val rewardedReady: Boolean get() = rewarded != null

    /** Shows a rewarded ad; [onReward] fires only if the user earns the reward. */
    fun showRewarded(activity: Activity, onReward: () -> Unit) {
        val ad = rewarded ?: run { preloadRewarded(); return }
        ad.fullScreenContentCallback = object : FullScreenContentCallback() {
            override fun onAdDismissedFullScreenContent() {
                rewarded = null
                preloadRewarded()
            }

            override fun onAdFailedToShowFullScreenContent(error: AdError) {
                rewarded = null
                preloadRewarded()
            }
        }
        ad.show(activity) { onReward() }
    }

    private companion object {
        const val MIN_INTERVAL_MS = 3 * 60 * 1000L
    }
}
