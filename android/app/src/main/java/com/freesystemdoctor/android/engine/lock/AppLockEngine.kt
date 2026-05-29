package com.freesystemdoctor.android.engine.lock

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.appLockDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_app_lock")

/**
 * Persistence + permission gateway for App Lock. The actual "watch foreground apps" loop
 * runs in [com.freesystemdoctor.android.service.AppLockService]; this engine just owns the
 * locked-packages list and the intents the UI needs to request permissions.
 */
class AppLockEngine(private val context: Context) {

    private val enabledKey = booleanPreferencesKey("enabled")
    private val lockedKey = stringSetPreferencesKey("locked_packages")

    val enabled: Flow<Boolean> = context.appLockDataStore.data.map { it[enabledKey] ?: false }

    val lockedPackages: Flow<Set<String>> =
        context.appLockDataStore.data.map { it[lockedKey] ?: emptySet() }

    suspend fun isEnabledOnce(): Boolean = enabled.first()

    suspend fun lockedOnce(): Set<String> = lockedPackages.first()

    suspend fun setEnabled(value: Boolean) {
        context.appLockDataStore.edit { it[enabledKey] = value }
    }

    suspend fun setLocked(packages: Set<String>) {
        context.appLockDataStore.edit { it[lockedKey] = packages }
    }

    suspend fun toggleLocked(pkg: String) {
        context.appLockDataStore.edit { prefs ->
            val current = prefs[lockedKey] ?: emptySet()
            prefs[lockedKey] = if (pkg in current) current - pkg else current + pkg
        }
    }

    fun canDrawOverlays(): Boolean = Settings.canDrawOverlays(context)

    fun overlaySettingsIntent(): Intent =
        Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}
