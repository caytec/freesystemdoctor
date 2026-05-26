package com.freesystemdoctor.android.ads

/**
 * AdMob unit IDs. These are Google's official TEST IDs — they always serve test ads and
 * are safe to ship in development. Replace each value with your real AdMob unit IDs (and
 * the app id in strings.xml: admob_app_id) before a production release, or you risk a
 * policy strike for clicking your own live ads.
 */
object AdUnits {
    const val BANNER = "ca-app-pub-3940256099942544/9214589741"
    const val INTERSTITIAL = "ca-app-pub-3940256099942544/1033173712"
    const val REWARDED = "ca-app-pub-3940256099942544/5224354917"
    const val APP_OPEN = "ca-app-pub-3940256099942544/9257395921"
}
