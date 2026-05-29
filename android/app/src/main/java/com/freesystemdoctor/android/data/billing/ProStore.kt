package com.freesystemdoctor.android.data.billing

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.proDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_pro")

/**
 * Caches entitlement locally so the UI can gate features without waiting for a billing
 * round-trip. The authoritative source is always Google Play; [BillingManager] refreshes
 * this on every connection.
 *
 * Three unlock dimensions are layered on top of the basic Pro entitlement:
 *  - [rewardUntil] — legacy global advanced-mode unlock from Update 7 (grandfathered).
 *  - [trialUntil] / [trialUsed] — one-time 3-day Pro trial granted via rewarded ad.
 *  - [toolUnlocks] — per-tool 24h unlocks granted via rewarded ad, keyed by nav route.
 */
class ProStore(private val context: Context) {

    private val proKey = booleanPreferencesKey("is_pro")
    private val rewardUntilKey = longPreferencesKey("advanced_reward_until")
    private val trialUntilKey = longPreferencesKey("trial_until")
    private val trialUsedKey = booleanPreferencesKey("trial_used")
    private val trialExpiryNoticeShownKey = booleanPreferencesKey("trial_expiry_notice_shown")
    private val toolUnlocksKey = stringSetPreferencesKey("tool_unlocks")
    private val lastForecastWarnAtKey = longPreferencesKey("last_forecast_warn_at")

    val isPro: Flow<Boolean> = context.proDataStore.data.map { it[proKey] ?: false }

    /** Epoch millis until which the legacy advanced-mode unlock is active. */
    val rewardUntil: Flow<Long> = context.proDataStore.data.map { it[rewardUntilKey] ?: 0L }

    /** Epoch millis until which the 3-day Pro trial is active. */
    val trialUntil: Flow<Long> = context.proDataStore.data.map { it[trialUntilKey] ?: 0L }

    /** True once the user has consumed their one-time Pro trial. */
    val trialUsed: Flow<Boolean> = context.proDataStore.data.map { it[trialUsedKey] ?: false }

    /** True once the trial-expired sheet has been shown after a trial ended. */
    val trialExpiryNoticeShown: Flow<Boolean> =
        context.proDataStore.data.map { it[trialExpiryNoticeShownKey] ?: false }

    /**
     * Per-tool unlock expiries keyed by nav route. Entries are pruned on emission so the UI
     * never sees stale unlocks; this is best-effort — the gating logic should still re-check
     * `expiry > now` at call sites for correctness across long-lived flows.
     */
    val toolUnlocks: Flow<Map<String, Long>> = context.proDataStore.data.map { prefs ->
        val now = System.currentTimeMillis()
        (prefs[toolUnlocksKey] ?: emptySet())
            .mapNotNull { entry ->
                val sep = entry.lastIndexOf(':')
                if (sep <= 0) return@mapNotNull null
                val route = entry.substring(0, sep)
                val expiry = entry.substring(sep + 1).toLongOrNull() ?: return@mapNotNull null
                if (expiry <= now) null else route to expiry
            }
            .toMap()
    }

    /** Epoch millis of the last storage forecast warning shown (debounce). */
    val lastForecastWarnAt: Flow<Long> =
        context.proDataStore.data.map { it[lastForecastWarnAtKey] ?: 0L }

    suspend fun setPro(value: Boolean) {
        context.proDataStore.edit { it[proKey] = value }
    }

    suspend fun grantAdvancedReward(durationMillis: Long) {
        context.proDataStore.edit {
            it[rewardUntilKey] = System.currentTimeMillis() + durationMillis
        }
    }

    suspend fun grantToolUnlock(route: String, durationMillis: Long) {
        val now = System.currentTimeMillis()
        val newExpiry = now + durationMillis
        context.proDataStore.edit { prefs ->
            val kept = (prefs[toolUnlocksKey] ?: emptySet())
                .mapNotNull { entry ->
                    val sep = entry.lastIndexOf(':')
                    if (sep <= 0) return@mapNotNull null
                    val r = entry.substring(0, sep)
                    val e = entry.substring(sep + 1).toLongOrNull() ?: return@mapNotNull null
                    if (r == route || e <= now) null else entry
                }
                .toMutableSet()
            kept += "$route:$newExpiry"
            prefs[toolUnlocksKey] = kept
        }
    }

    suspend fun grantTrial(durationMillis: Long) {
        context.proDataStore.edit {
            it[trialUntilKey] = System.currentTimeMillis() + durationMillis
            it[trialUsedKey] = true
            it[trialExpiryNoticeShownKey] = false
        }
    }

    suspend fun markTrialExpiryNoticeShown() {
        context.proDataStore.edit { it[trialExpiryNoticeShownKey] = true }
    }

    suspend fun setLastForecastWarnAt(epochMillis: Long) {
        context.proDataStore.edit { it[lastForecastWarnAtKey] = epochMillis }
    }
}
