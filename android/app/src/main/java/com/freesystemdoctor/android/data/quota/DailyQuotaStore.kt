package com.freesystemdoctor.android.data.quota

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.quotaDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_quotas")

/**
 * Daily per-feature quotas for free-tier users. PRO removes the cap entirely; the
 * Composable [com.freesystemdoctor.android.ui.components.QuotaGate] handles the gating UX.
 *
 * Each key gets its own [DayBucketCounter] so counts reset independently at local midnight.
 */
class DailyQuotaStore(private val context: Context) {

    enum class Key(val limit: Int, internal val counter: DayBucketCounter) {
        PRIVACY_DEEP_AUDIT(3, DayBucketCounter("privacy_deep_audit")),
        PRIVACY_PROFILE_APPLY(1, DayBucketCounter("privacy_profile_apply")),
        MODE_SWITCH(1, DayBucketCounter("mode_switch")),
        BROWSER_CLEAN(1, DayBucketCounter("browser_clean")),
    }

    fun used(key: Key): Flow<Int> = context.quotaDataStore.data.map { prefs ->
        key.counter.peek(prefs, DayBucketCounter.today())
    }

    suspend fun usedOnce(key: Key): Int = used(key).first()

    suspend fun consume(key: Key): Int {
        var newCount = 0
        context.quotaDataStore.edit { prefs ->
            newCount = key.counter.consume(prefs, DayBucketCounter.today())
        }
        return newCount
    }

    /** True if the next [consume] for [key] would exceed its daily limit. */
    suspend fun isExhausted(key: Key): Boolean = usedOnce(key) >= key.limit
}
