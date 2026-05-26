package com.freesystemdoctor.android.ads

import android.app.Activity
import android.app.Application
import android.os.Bundle
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.ProcessLifecycleOwner
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.google.android.gms.ads.AdError
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.FullScreenContentCallback
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.appopen.AppOpenAd

/**
 * Shows an App Open ad when the user brings the app back to the foreground.
 * Play-safe guards: never on the cold start (don't interrupt launch), never while
 * another full-screen ad is showing, a frequency cap, and a one-shot [suppressNextShow]
 * used before our own system dialogs (billing, delete-request) so the user doesn't see
 * an ad merely for returning from a flow we triggered. No ads for Pro / before consent.
 */
class AppOpenAdManager(private val application: Application) :
    Application.ActivityLifecycleCallbacks, DefaultLifecycleObserver {

    private var appOpenAd: AppOpenAd? = null
    private var isLoading = false
    private var isShowingAd = false
    private var currentActivity: Activity? = null
    private var firstStartHandled = false
    private var suppressOnce = false
    private var lastShownAt = 0L

    fun register() {
        application.registerActivityLifecycleCallbacks(this)
        ProcessLifecycleOwner.get().lifecycle.addObserver(this)
    }

    fun suppressNextShow() {
        suppressOnce = true
    }

    fun onAdsEnabled() = loadAd()

    private fun allowed(): Boolean =
        ServiceLocator.adsController.canRequestAds && !ServiceLocator.billingManager.isPro.value

    private fun loadAd() {
        if (isLoading || appOpenAd != null || !allowed()) return
        isLoading = true
        AppOpenAd.load(
            application,
            AdUnits.APP_OPEN,
            AdRequest.Builder().build(),
            object : AppOpenAd.AppOpenAdLoadCallback() {
                override fun onAdLoaded(ad: AppOpenAd) {
                    appOpenAd = ad
                    isLoading = false
                }

                override fun onAdFailedToLoad(error: LoadAdError) {
                    isLoading = false
                }
            },
        )
    }

    override fun onStart(owner: LifecycleOwner) {
        if (!firstStartHandled) {
            firstStartHandled = true
            loadAd()
            return
        }
        showIfAvailable()
    }

    private fun showIfAvailable() {
        if (suppressOnce) {
            suppressOnce = false
            loadAd()
            return
        }
        if (isShowingAd || !allowed()) {
            loadAd()
            return
        }
        if (System.currentTimeMillis() - lastShownAt < MIN_INTERVAL_MS) return
        val ad = appOpenAd ?: run { loadAd(); return }
        val activity = currentActivity ?: return
        ad.fullScreenContentCallback = object : FullScreenContentCallback() {
            override fun onAdShowedFullScreenContent() {
                isShowingAd = true
            }

            override fun onAdDismissedFullScreenContent() {
                appOpenAd = null
                isShowingAd = false
                loadAd()
            }

            override fun onAdFailedToShowFullScreenContent(error: AdError) {
                appOpenAd = null
                isShowingAd = false
                loadAd()
            }
        }
        lastShownAt = System.currentTimeMillis()
        ad.show(activity)
    }

    override fun onActivityResumed(activity: Activity) {
        if (!isShowingAd) currentActivity = activity
    }

    override fun onActivityStarted(activity: Activity) {
        if (!isShowingAd) currentActivity = activity
    }

    override fun onActivityDestroyed(activity: Activity) {
        if (currentActivity === activity) currentActivity = null
    }

    override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) {}
    override fun onActivityPaused(activity: Activity) {}
    override fun onActivityStopped(activity: Activity) {}
    override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) {}

    private companion object {
        const val MIN_INTERVAL_MS = 4 * 60 * 1000L
    }
}
