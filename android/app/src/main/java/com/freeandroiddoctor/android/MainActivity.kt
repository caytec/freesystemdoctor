package com.freeandroiddoctor.android

import android.animation.AnimatorSet
import android.animation.ObjectAnimator
import android.os.Build
import android.os.Bundle
import android.view.animation.AccelerateInterpolator
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.animation.doOnEnd
import androidx.fragment.app.FragmentActivity
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.freeandroiddoctor.android.ads.ConsentManager
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.data.settings.AppSettings
import com.freeandroiddoctor.android.ui.navigation.MainScaffold
import com.freeandroiddoctor.android.ui.navigation.ORGANIZER_CATEGORY_EXTRA
import com.freeandroiddoctor.android.ui.onboarding.OnboardingScreen
import com.freeandroiddoctor.android.ui.onboarding.TutorialScreen
import com.freeandroiddoctor.android.ui.theme.FsdTheme
import com.freeandroiddoctor.android.ui.whatsnew.WhatsNewHost
import kotlinx.coroutines.launch

class MainActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        val splashScreen = installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Fade + shrink the splash icon out instead of the default hard cut, so
        // the handoff to the first composed frame reads as one continuous motion.
        splashScreen.setOnExitAnimationListener { provider ->
            val icon = provider.iconView
            AnimatorSet().apply {
                playTogether(
                    ObjectAnimator.ofFloat(icon, "alpha", 1f, 0f),
                    ObjectAnimator.ofFloat(icon, "scaleX", 1f, 1.15f),
                    ObjectAnimator.ofFloat(icon, "scaleY", 1f, 1.15f),
                )
                duration = 220L
                interpolator = AccelerateInterpolator()
                doOnEnd { provider.remove() }
            }.start()
        }

        // Anti-tapjacking: while our UI is on top, hide untrusted overlay windows
        // drawn by other apps (SYSTEM_ALERT_WINDOW). Protects sensitive in-app
        // surfaces (vault unlock, paywall/purchase) from overlay-based click hijack.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            window.setHideOverlayWindows(true)
        }

        // Verify Pro entitlement with Google Play, then resolve ad consent before any ads.
        ServiceLocator.billingManager.connect()
        ConsentManager(this).gather(this) { canRequestAds ->
            ServiceLocator.adsController.initialize(canRequestAds)
            ServiceLocator.appOpenAdManager.onAdsEnabled()
        }

        setContent {
            val settings by ServiceLocator.settingsRepository.settings
                .collectAsState(initial = AppSettings())
            var tutorialComplete by remember { mutableStateOf(false) }
            var onboardingComplete by remember { mutableStateOf(false) }
            val scope = rememberCoroutineScope()
            // Set when this activity was launched from a pinned Organizer category shortcut.
            val pendingOrganizerCategory = remember { intent.getStringExtra(ORGANIZER_CATEGORY_EXTRA) }

            val systemDark = isSystemInDarkTheme()
            val useDark = if (settings.followSystem) systemDark else settings.darkTheme
            FsdTheme(darkTheme = useDark) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    when {
                        // Permission-free "how to use this app" walkthrough, shown once before
                        // the permissions-request screen so system prompts don't interrupt it.
                        !settings.tutorialDone && !tutorialComplete -> {
                            TutorialScreen(onDone = {
                                tutorialComplete = true
                                scope.launch { ServiceLocator.settingsRepository.setTutorialDone(true) }
                            })
                        }
                        settings.onboardingDone || onboardingComplete -> {
                            MainScaffold(pendingOrganizerCategory = pendingOrganizerCategory)
                            WhatsNewHost()
                        }
                        else -> {
                            OnboardingScreen(onContinue = { onboardingComplete = true })
                        }
                    }
                }
            }
        }
    }
}
