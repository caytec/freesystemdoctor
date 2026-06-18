package com.freesystemdoctor.android.ads

import com.freesystemdoctor.android.BuildConfig

/**
 * AdMob unit IDs — values come from android/admob.properties (git-ignored) via Gradle
 * buildConfigField. The committed default is Google's official TEST IDs, which always
 * serve test ads and are safe to ship in development.
 */
object AdUnits {
    val BANNER: String = BuildConfig.ADMOB_BANNER_ID
    val INTERSTITIAL: String = BuildConfig.ADMOB_INTERSTITIAL_ID
    val REWARDED: String = BuildConfig.ADMOB_REWARDED_ID
    val APP_OPEN: String = BuildConfig.ADMOB_APPOPEN_ID
    val NATIVE: String = BuildConfig.ADMOB_NATIVE_ID
}
