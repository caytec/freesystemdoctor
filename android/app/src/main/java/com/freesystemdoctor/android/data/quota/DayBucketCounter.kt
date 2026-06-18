package com.freesystemdoctor.android.data.quota

import androidx.datastore.preferences.core.MutablePreferences
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Reusable "consume N per local day" counter, persisted alongside any other DataStore
 * preferences. Keeps a paired (dayKey, countKey) entry — when the calendar day changes
 * locally the count resets automatically.
 *
 * Used by both the AI assistant daily cap and the new Privacy/Modes/Auto-Rules quotas
 * introduced in Update 14.
 */
class DayBucketCounter(name: String) {

    private val dayKey = stringPreferencesKey("${name}_day")
    private val countKey = intPreferencesKey("${name}_count")

    fun peek(prefs: Preferences, today: String): Int {
        val storedDay = prefs[dayKey]
        return if (storedDay == today) prefs[countKey] ?: 0 else 0
    }

    /** Bumps the counter for [today]. Returns the new count. */
    fun consume(prefs: MutablePreferences, today: String): Int {
        val storedDay = prefs[dayKey]
        val current = if (storedDay == today) prefs[countKey] ?: 0 else 0
        val next = current + 1
        prefs[dayKey] = today
        prefs[countKey] = next
        return next
    }

    /** Refunds one use for [today], floor of 0. Returns the new count. */
    fun refund(prefs: MutablePreferences, today: String): Int {
        val storedDay = prefs[dayKey]
        val current = if (storedDay == today) prefs[countKey] ?: 0 else 0
        val next = (current - 1).coerceAtLeast(0)
        prefs[dayKey] = today
        prefs[countKey] = next
        return next
    }

    companion object {
        private val LOCAL_DAY: SimpleDateFormat by lazy {
            SimpleDateFormat("yyyy-MM-dd", Locale.US)
        }

        fun today(): String = LOCAL_DAY.format(Date())
    }
}
