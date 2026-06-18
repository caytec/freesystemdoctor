package com.freesystemdoctor.android.ui.components

import android.view.LayoutInflater
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ads.AdUnits
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.google.android.gms.ads.AdListener
import com.google.android.gms.ads.AdLoader
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.nativead.NativeAd
import com.google.android.gms.ads.nativead.NativeAdView

/**
 * Full-width AdMob Native Advanced card used inline in the Tools grid. Loads one ad on
 * first composition, releases it on dispose. Renders nothing for Pro users or before
 * UMP consent — same gate as [BannerAd].
 *
 * Layout lives in res/layout/ad_native_card.xml because AdMob requires a real
 * [NativeAdView] root with child view IDs for click-tracking attribution.
 */
@Composable
fun NativeAdCard(modifier: Modifier = Modifier) {
    val ctx = LocalContext.current
    val ads = ServiceLocator.adsController
    val isPro by ServiceLocator.billingManager.isPro.collectAsStateWithLifecycle()

    if (isPro || !ads.canRequestAds) return

    var nativeAd by remember { mutableStateOf<NativeAd?>(null) }

    DisposableEffect(Unit) {
        val loader = AdLoader.Builder(ctx, AdUnits.NATIVE)
            .forNativeAd { ad ->
                nativeAd?.destroy()
                nativeAd = ad
            }
            .withAdListener(object : AdListener() {
                override fun onAdFailedToLoad(error: LoadAdError) {
                    nativeAd?.destroy()
                    nativeAd = null
                }
            })
            .build()
        loader.loadAd(AdRequest.Builder().build())
        onDispose {
            nativeAd?.destroy()
            nativeAd = null
        }
    }

    val ad = nativeAd ?: return
    val containerColor = MaterialTheme.colorScheme.surfaceContainer
    val shape = MaterialTheme.shapes.medium

    AndroidView(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .background(containerColor),
        factory = { c ->
            val adView = LayoutInflater.from(c)
                .inflate(R.layout.ad_native_card, null) as NativeAdView
            adView.headlineView = adView.findViewById<TextView>(R.id.ad_headline)
            adView.bodyView = adView.findViewById<TextView>(R.id.ad_body)
            adView.callToActionView = adView.findViewById<Button>(R.id.ad_cta)
            adView.iconView = adView.findViewById<ImageView>(R.id.ad_icon)
            adView
        },
        update = { adView ->
            (adView.headlineView as TextView).text = ad.headline
            val bodyView = adView.bodyView as TextView
            ad.body?.let { bodyView.text = it } ?: run { bodyView.text = "" }
            val cta = adView.callToActionView as Button
            ad.callToAction?.let { cta.text = it } ?: run { cta.text = "" }
            val iconView = adView.iconView as ImageView
            ad.icon?.drawable?.let { iconView.setImageDrawable(it) }
                ?: run { iconView.setImageDrawable(null) }
            adView.setNativeAd(ad)
        },
    )
}
