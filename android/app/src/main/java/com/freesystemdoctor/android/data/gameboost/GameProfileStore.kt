package com.freesystemdoctor.android.data.gameboost

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.gameBoostDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_game_boost")

/**
 * Persists the user's Game Booster preferences: which packages are "boosted games",
 * whether auto-trigger is on, and whether to enter DND for the session. The actual
 * session lifecycle (foreground service + DND apply/restore) lives in
 * [com.freesystemdoctor.android.service.GameBoostService].
 */
class GameProfileStore(private val context: Context) {

    private val gamesKey = stringSetPreferencesKey("boosted_packages")
    private val autoTriggerKey = booleanPreferencesKey("auto_trigger")
    private val enterDndKey = booleanPreferencesKey("enter_dnd")

    val boostedPackages: Flow<Set<String>> =
        context.gameBoostDataStore.data.map { it[gamesKey] ?: emptySet() }

    val autoTrigger: Flow<Boolean> =
        context.gameBoostDataStore.data.map { it[autoTriggerKey] ?: false }

    val enterDnd: Flow<Boolean> =
        context.gameBoostDataStore.data.map { it[enterDndKey] ?: true }

    suspend fun boostedOnce(): Set<String> = boostedPackages.first()
    suspend fun autoTriggerOnce(): Boolean = autoTrigger.first()
    suspend fun enterDndOnce(): Boolean = enterDnd.first()

    suspend fun togglePackage(pkg: String) {
        context.gameBoostDataStore.edit { prefs ->
            val current = prefs[gamesKey] ?: emptySet()
            prefs[gamesKey] = if (pkg in current) current - pkg else current + pkg
        }
    }

    suspend fun setAutoTrigger(value: Boolean) {
        context.gameBoostDataStore.edit { it[autoTriggerKey] = value }
    }

    suspend fun setEnterDnd(value: Boolean) {
        context.gameBoostDataStore.edit { it[enterDndKey] = value }
    }
}
