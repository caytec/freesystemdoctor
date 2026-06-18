package com.freesystemdoctor.android.ui.review

import android.app.Activity
import android.util.Log
import com.freesystemdoctor.android.data.settings.SettingsRepository
import com.google.android.play.core.ktx.launchReview
import com.google.android.play.core.ktx.requestReview
import com.google.android.play.core.review.ReviewManagerFactory
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

private const val MIN_CLEANS_BEFORE_PROMPT = 3
private val MIN_INTERVAL_BETWEEN_PROMPTS_MS = TimeUnit.DAYS.toMillis(90)
private const val TAG = "InAppReview"

/**
 * Requests an in-app review prompt after the user has completed at least 3 cleans
 * and not been asked in the last 90 days. The Play Core API additionally rate-limits
 * itself, so the actual prompt may not appear — we just request and move on.
 *
 * Safe to call from any successful clean completion; bails out silently if Play Store
 * is unavailable (sideload, emulator without Play, throttled).
 */
suspend fun maybeRequestReview(activity: Activity, settings: SettingsRepository) {
    val count = settings.incrementCleanCount()
    if (count < MIN_CLEANS_BEFORE_PROMPT) return

    val lastIso = settings.lastReviewPromptDateOnce()
    if (lastIso.isNotEmpty()) {
        val lastEpoch = runCatching { ISO.parse(lastIso)?.time }.getOrNull() ?: 0L
        if (lastEpoch > 0L &&
            System.currentTimeMillis() - lastEpoch < MIN_INTERVAL_BETWEEN_PROMPTS_MS
        ) return
    }

    try {
        val manager = ReviewManagerFactory.create(activity)
        val info = manager.requestReview()
        manager.launchReview(activity, info)
        settings.recordReviewPromptDate(ISO.format(Date()))
    } catch (t: Throwable) {
        Log.w(TAG, "Review prompt unavailable: ${t.message}")
    }
}

private val ISO = SimpleDateFormat("yyyy-MM-dd", Locale.US)
