package com.freesystemdoctor.android.ads

import android.app.Activity
import com.google.android.ump.ConsentInformation
import com.google.android.ump.ConsentRequestParameters
import com.google.android.ump.UserMessagingPlatform

/**
 * Google User Messaging Platform consent flow — required to serve personalised ads in
 * the EEA/UK. Must run before ads are requested.
 */
class ConsentManager(activity: Activity) {

    private val consentInformation: ConsentInformation =
        UserMessagingPlatform.getConsentInformation(activity)

    fun gather(activity: Activity, onResolved: (canRequestAds: Boolean) -> Unit) {
        val params = ConsentRequestParameters.Builder().build()
        consentInformation.requestConsentInfoUpdate(
            activity,
            params,
            {
                UserMessagingPlatform.loadAndShowConsentFormIfRequired(activity) {
                    onResolved(consentInformation.canRequestAds())
                }
            },
            {
                // On failure, fall back to whatever the SDK already knows.
                onResolved(consentInformation.canRequestAds())
            },
        )
    }
}
