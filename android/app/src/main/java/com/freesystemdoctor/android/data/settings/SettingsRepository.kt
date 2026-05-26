package com.freesystemdoctor.android.data.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.freesystemdoctor.android.ai.AiProvider
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_settings")

data class AppSettings(
    val onboardingDone: Boolean = false,
    val darkTheme: Boolean = true,
    val aiProvider: AiProvider = AiProvider.GROQ,
    val scheduledCleaning: Boolean = false,
)

class SettingsRepository(private val context: Context) {

    private object Keys {
        val ONBOARDING_DONE = booleanPreferencesKey("onboarding_done")
        val DARK_THEME = booleanPreferencesKey("dark_theme")
        val AI_PROVIDER = stringPreferencesKey("ai_provider")
        val SCHEDULED_CLEANING = booleanPreferencesKey("scheduled_cleaning")
    }

    val settings: Flow<AppSettings> = context.dataStore.data.map { prefs ->
        AppSettings(
            onboardingDone = prefs[Keys.ONBOARDING_DONE] ?: false,
            darkTheme = prefs[Keys.DARK_THEME] ?: true,
            aiProvider = prefs[Keys.AI_PROVIDER]
                ?.let { runCatching { AiProvider.valueOf(it) }.getOrNull() }
                ?: AiProvider.GROQ,
            scheduledCleaning = prefs[Keys.SCHEDULED_CLEANING] ?: false,
        )
    }

    suspend fun setOnboardingDone(done: Boolean) {
        context.dataStore.edit { it[Keys.ONBOARDING_DONE] = done }
    }

    suspend fun setDarkTheme(enabled: Boolean) {
        context.dataStore.edit { it[Keys.DARK_THEME] = enabled }
    }

    suspend fun setAiProvider(provider: AiProvider) {
        context.dataStore.edit { it[Keys.AI_PROVIDER] = provider.name }
    }

    suspend fun setScheduledCleaning(enabled: Boolean) {
        context.dataStore.edit { it[Keys.SCHEDULED_CLEANING] = enabled }
    }
}
