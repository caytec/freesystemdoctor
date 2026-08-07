package com.freeandroiddoctor.android.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.freeandroiddoctor.android.ads.AdUnits
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.AdSize
import com.google.android.gms.ads.AdView

/** Adaptive anchored banner. Renders nothing for Pro users or before ad consent. */
@Composable
fun BannerAd(modifier: Modifier = Modifier) {
    val configuration = LocalConfiguration.current
    val ads = ServiceLocator.adsController
    val isPro by ServiceLocator.billingManager.isPro.collectAsStateWithLifecycle()

    if (isPro || !ads.canRequestAds) return

    AndroidView(
        modifier = modifier.fillMaxWidth(),
        factory = { ctx ->
            AdView(ctx).apply {
                val width = configuration.screenWidthDp
                setAdSize(
                    AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(ctx, width),
                )
                adUnitId = AdUnits.BANNER
                loadAd(AdRequest.Builder().build())
            }
        },
    )
}
