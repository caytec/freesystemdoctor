package com.freesystemdoctor.android.data.billing

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.proDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_pro")

/**
 * Caches entitlement locally so the UI can gate features without waiting for a billing
 * round-trip. The authoritative source is always Google Play; [BillingManager] refreshes
 * this on every connection.
 */
class ProStore(private val context: Context) {

    private val proKey = booleanPreferencesKey("is_pro")
    private val rewardUntilKey = longPreferencesKey("advanced_reward_until")

    val isPro: Flow<Boolean> = context.proDataStore.data.map { it[proKey] ?: false }

    /** Epoch millis until which a rewarded-ad unlock of advanced mode is active. */
    val rewardUntil: Flow<Long> = context.proDataStore.data.map { it[rewardUntilKey] ?: 0L }

    suspend fun setPro(value: Boolean) {
        context.proDataStore.edit { it[proKey] = value }
    }

    suspend fun grantAdvancedReward(durationMillis: Long) {
        context.proDataStore.edit {
            it[rewardUntilKey] = System.currentTimeMillis() + durationMillis
        }
    }
}
