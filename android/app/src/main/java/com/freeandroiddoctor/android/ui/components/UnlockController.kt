package com.freeandroiddoctor.android.ui.components

import androidx.compose.runtime.compositionLocalOf
import com.freeandroiddoctor.android.data.quota.DailyQuotaStore

/**
 * App-wide hook used by feature screens to ask the host to show the unlock sheet for a
 * locked tool. The host (typically [com.freeandroiddoctor.android.MainActivity]) installs a
 * real controller; everything below it just calls `request(route)`.
 *
 * Pass [quotaKey] when the trigger was a daily-quota exhaustion (Update 14) — the sheet
 * will surface a "watch ad → +1 use today" option in addition to the regular unlocks.
 */
interface UnlockController {
    fun request(
        route: String,
        labelRes: Int? = null,
        quotaKey: DailyQuotaStore.Key? = null,
    )
}

private val NoopController = object : UnlockController {
    override fun request(route: String, labelRes: Int?, quotaKey: DailyQuotaStore.Key?) = Unit
}

val LocalUnlockController = compositionLocalOf<UnlockController> { NoopController }
