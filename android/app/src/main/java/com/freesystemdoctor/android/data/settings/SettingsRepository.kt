package com.freesystemdoctor.android.data.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.freesystemdoctor.android.ai.AiProvider
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_settings")

data class AppSettings(
    val onboardingDone: Boolean = false,
    val darkTheme: Boolean = true,
    val followSystem: Boolean = false,
    val aiProvider: AiProvider = AiProvider.GROQ,
    val scheduledCleaning: Boolean = false,
    val advancedMode: Boolean = false,
    val monitorEnabled: Boolean = false,
    val lastSeenVersionCode: Int = 0,
    val batteryAlarmsEnabled: Boolean = false,
    val batteryAlarmLow: Int = 15,
    val batteryAlarmFull: Int = 80,
    val shizukuEnabled: Boolean = false,
    val shizukuSnackbarShown: Boolean = false,
)

class SettingsRepository(private val context: Context) {

    private object Keys {
        val ONBOARDING_DONE = booleanPreferencesKey("onboarding_done")
        val DARK_THEME = booleanPreferencesKey("dark_theme")
        val FOLLOW_SYSTEM = booleanPreferencesKey("follow_system")
        val AI_PROVIDER = stringPreferencesKey("ai_provider")
        val SCHEDULED_CLEANING = booleanPreferencesKey("scheduled_cleaning")
        val ADVANCED_MODE = booleanPreferencesKey("advanced_mode")
        val MONITOR_ENABLED = booleanPreferencesKey("monitor_enabled")
        val LAST_SEEN_VERSION = intPreferencesKey("last_seen_version_code")
        val BATTERY_ALARMS = booleanPreferencesKey("battery_alarms_enabled")
        val BATTERY_ALARM_LOW = intPreferencesKey("battery_alarm_low")
        val BATTERY_ALARM_FULL = intPreferencesKey("battery_alarm_full")
        val AI_USAGE_DAY = stringPreferencesKey("ai_usage_day")
        val AI_USAGE_COUNT = intPreferencesKey("ai_usage_count")
        val SHIZUKU_ENABLED = booleanPreferencesKey("shizuku_enabled")
        val SHIZUKU_SNACKBAR_SHOWN = booleanPreferencesKey("shizuku_snackbar_shown")
    }

    val settings: Flow<AppSettings> = context.dataStore.data.map { prefs ->
        AppSettings(
            onboardingDone = prefs[Keys.ONBOARDING_DONE] ?: false,
            darkTheme = prefs[Keys.DARK_THEME] ?: true,
            followSystem = prefs[Keys.FOLLOW_SYSTEM] ?: false,
            aiProvider = prefs[Keys.AI_PROVIDER]
                ?.let { runCatching { AiProvider.valueOf(it) }.getOrNull() }
                ?: AiProvider.GROQ,
            scheduledCleaning = prefs[Keys.SCHEDULED_CLEANING] ?: false,
            advancedMode = prefs[Keys.ADVANCED_MODE] ?: false,
            monitorEnabled = prefs[Keys.MONITOR_ENABLED] ?: false,
            lastSeenVersionCode = prefs[Keys.LAST_SEEN_VERSION] ?: 0,
            batteryAlarmsEnabled = prefs[Keys.BATTERY_ALARMS] ?: false,
            batteryAlarmLow = prefs[Keys.BATTERY_ALARM_LOW] ?: 15,
            batteryAlarmFull = prefs[Keys.BATTERY_ALARM_FULL] ?: 80,
            shizukuEnabled = prefs[Keys.SHIZUKU_ENABLED] ?: false,
            shizukuSnackbarShown = prefs[Keys.SHIZUKU_SNACKBAR_SHOWN] ?: false,
        )
    }

    suspend fun setOnboardingDone(done: Boolean) {
        context.dataStore.edit { it[Keys.ONBOARDING_DONE] = done }
    }

    suspend fun setDarkTheme(enabled: Boolean) {
        context.dataStore.edit { it[Keys.DARK_THEME] = enabled }
    }

    suspend fun setFollowSystem(enabled: Boolean) {
        context.dataStore.edit { it[Keys.FOLLOW_SYSTEM] = enabled }
    }

    suspend fun setAiProvider(provider: AiProvider) {
        context.dataStore.edit { it[Keys.AI_PROVIDER] = provider.name }
    }

    suspend fun setScheduledCleaning(enabled: Boolean) {
        context.dataStore.edit { it[Keys.SCHEDULED_CLEANING] = enabled }
    }

    suspend fun setAdvancedMode(enabled: Boolean) {
        context.dataStore.edit { it[Keys.ADVANCED_MODE] = enabled }
    }

    suspend fun setMonitorEnabled(enabled: Boolean) {
        context.dataStore.edit { it[Keys.MONITOR_ENABLED] = enabled }
    }

    suspend fun setLastSeenVersionCode(code: Int) {
        context.dataStore.edit { it[Keys.LAST_SEEN_VERSION] = code }
    }

    suspend fun setBatteryAlarms(enabled: Boolean) {
        context.dataStore.edit { it[Keys.BATTERY_ALARMS] = enabled }
    }

    suspend fun setBatteryAlarmThresholds(low: Int, full: Int) {
        context.dataStore.edit {
            it[Keys.BATTERY_ALARM_LOW] = low.coerceIn(5, 50)
            it[Keys.BATTERY_ALARM_FULL] = full.coerceIn(50, 100)
        }
    }

    suspend fun setShizukuEnabled(enabled: Boolean) {
        context.dataStore.edit { it[Keys.SHIZUKU_ENABLED] = enabled }
    }

    suspend fun setShizukuSnackbarShown(shown: Boolean) {
        context.dataStore.edit { it[Keys.SHIZUKU_SNACKBAR_SHOWN] = shown }
    }

    /**
     * Returns today's AI analysis count and bumps it. Used to enforce the free-tier daily cap
     * (PRO is unlimited; gating lives in [com.freesystemdoctor.android.ui.assistant.AssistantViewModel]).
     */
    suspend fun consumeAiUsage(today: String): Int {
        var newCount = 0
        context.dataStore.edit { prefs ->
            val storedDay = prefs[Keys.AI_USAGE_DAY]
            val current = if (storedDay == today) prefs[Keys.AI_USAGE_COUNT] ?: 0 else 0
            newCount = current + 1
            prefs[Keys.AI_USAGE_DAY] = today
            prefs[Keys.AI_USAGE_COUNT] = newCount
        }
        return newCount
    }

    suspend fun peekAiUsage(today: String): Int {
        val prefs = context.dataStore.data.map {
            val day = it[Keys.AI_USAGE_DAY]
            if (day == today) it[Keys.AI_USAGE_COUNT] ?: 0 else 0
        }
        return prefs.first()
    }
}
