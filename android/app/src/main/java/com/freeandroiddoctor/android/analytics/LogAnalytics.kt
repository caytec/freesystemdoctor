package com.freeandroiddoctor.android.analytics

import android.util.Log
import com.freeandroiddoctor.android.BuildConfig

/** No-op implementation that logs events to Logcat. Replace with FirebaseAnalytics once
 *  google-services.json is wired up per product flavor. */
class LogAnalytics : Analytics {
    override fun log(event: AnalyticsEvent) {
        // Debug-only: release logcat must not leak paywall routes or SKUs.
        if (BuildConfig.DEBUG) Log.d(TAG, event.toString())
    }

    private companion object {
        const val TAG = "FSD_Analytics"
    }
}
