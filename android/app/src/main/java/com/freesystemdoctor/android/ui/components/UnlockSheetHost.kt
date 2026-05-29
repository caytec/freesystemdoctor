package com.freesystemdoctor.android.ui.components

import android.app.Activity
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.ui.navigation.ROUTE_PRO
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

/**
 * Wraps the app's nav graph and installs a real [UnlockController] in [LocalUnlockController].
 * Any composable below this host can call `LocalUnlockController.current.request(route)` to
 * surface the unlock sheet for a locked tool.
 *
 * The host also watches for the one-time "trial just expired" event and auto-shows the sheet
 * with a soft notice the next time the user lands here (typically the Tools tab).
 *
 * @param navigateToPro called when the user picks "Buy Pro forever" so we can route to
 *                     [ROUTE_PRO] without coupling to a NavController instance here.
 */
@Composable
fun UnlockSheetHost(
    navigateToPro: () -> Unit,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val activity = context as? Activity
    val scope = rememberCoroutineScope()

    val billing = ServiceLocator.billingManager
    val ads = ServiceLocator.adsController
    val proStore = ServiceLocator.proStore

    var request by remember { mutableStateOf<UnlockRequest?>(null) }

    val controller = remember {
        object : UnlockController {
            override fun request(route: String, labelRes: Int?) {
                request = UnlockRequest(route, labelRes)
            }
        }
    }

    // Surface the post-trial-expiry notice once.
    val trialJustExpired by remember { proStore.trialExpiryNoticeShown }.collectAsState(initial = true)
    val trialUntil by remember { proStore.trialUntil }.collectAsState(initial = 0L)
    val trialUsed by remember { proStore.trialUsed }.collectAsState(initial = false)
    val isPro by billing.isPro.collectAsState()

    val showExpiredNotice = !isPro && trialUsed && trialUntil in 1L..System.currentTimeMillis() && !trialJustExpired
    LaunchedEffect(showExpiredNotice) {
        if (showExpiredNotice && request == null) {
            request = UnlockRequest(route = "__trial_expired__", labelRes = null)
        }
    }

    CompositionLocalProvider(LocalUnlockController provides controller) {
        content()
    }

    val current = request
    if (current != null) {
        UnlockSheet(
            request = current,
            rewardedReady = ads.rewardedReady,
            trialUsed = trialUsed,
            trialJustExpired = current.route == "__trial_expired__",
            onWatchAdForTool = {
                activity?.let { act ->
                    ads.showRewarded(act) {
                        scope.launch {
                            proStore.grantToolUnlock(current.route, TimeUnit.HOURS.toMillis(24))
                        }
                    }
                }
                request = null
            },
            onWatchAdForTrial = {
                activity?.let { act ->
                    ads.showRewarded(act) {
                        scope.launch {
                            proStore.grantTrial(TimeUnit.DAYS.toMillis(3))
                        }
                    }
                }
                request = null
            },
            onBuyPro = {
                request = null
                navigateToPro()
            },
            onRestore = {
                billing.restore()
                request = null
            },
            onDismiss = {
                if (current.route == "__trial_expired__") {
                    scope.launch { proStore.markTrialExpiryNoticeShown() }
                }
                request = null
            },
        )
    }
}
