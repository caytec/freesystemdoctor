package com.freesystemdoctor.android.analytics

import android.util.Log

/** No-op implementation that logs events to Logcat. Replace with FirebaseAnalytics once
 *  google-services.json is wired up per product flavor. */
class LogAnalytics : Analytics {
    override fun log(event: AnalyticsEvent) {
        Log.d(TAG, event.toString())
    }

    private companion object {
        const val TAG = "FSD_Analytics"
    }
}
