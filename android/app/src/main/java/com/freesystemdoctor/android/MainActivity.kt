package com.freesystemdoctor.android

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.fragment.app.FragmentActivity
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.freesystemdoctor.android.ads.ConsentManager
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.data.settings.AppSettings
import com.freesystemdoctor.android.ui.navigation.MainScaffold
import com.freesystemdoctor.android.ui.onboarding.OnboardingScreen
import com.freesystemdoctor.android.ui.theme.FsdTheme
import com.freesystemdoctor.android.ui.whatsnew.WhatsNewHost

class MainActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Verify Pro entitlement with Google Play, then resolve ad consent before any ads.
        ServiceLocator.billingManager.connect()
        ConsentManager(this).gather(this) { canRequestAds ->
            ServiceLocator.adsController.initialize(canRequestAds)
            ServiceLocator.appOpenAdManager.onAdsEnabled()
        }

        setContent {
            val settings by ServiceLocator.settingsRepository.settings
                .collectAsState(initial = AppSettings())
            var onboardingComplete by remember { mutableStateOf(false) }

            FsdTheme(darkTheme = settings.darkTheme) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    if (settings.onboardingDone || onboardingComplete) {
                        MainScaffold()
                        WhatsNewHost()
                    } else {
                        OnboardingScreen(onContinue = { onboardingComplete = true })
                    }
                }
            }
        }
    }
}
