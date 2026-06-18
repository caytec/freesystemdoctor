package com.freesystemdoctor.android.data.automation

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.serialization.Serializable
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.MapSerializer
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json

private val Context.autoRulesDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_auto_rules")

@Serializable
enum class AutoRuleTrigger {
    LOW_STORAGE,
    CHARGING_FULL,
    BOOT,
    WEEKLY_DEEP_SCAN,
    OPEN_WIFI_DETECTED,
    APP_INSTALLED,
}

@Serializable
enum class AutoRuleAction {
    NOTIFY_DEEP_SCAN,
    RUN_CACHE_CLEAN,
    ACTIVATE_MODE,
    NOTIFY_INSTALL_RISK,
}

@Serializable
data class AutoRule(
    val id: String,
    val labelKey: String,
    val trigger: AutoRuleTrigger,
    val action: AutoRuleAction,
    val triggerThreshold: Int = 10,
    val modeIdParam: String? = null,
    val enabled: Boolean = true,
    val isPro: Boolean = false,
)

class AutoRuleStore(private val context: Context) {

    private val rulesKey = stringPreferencesKey("auto_rules_json")
    private val lastFiredKey = stringPreferencesKey("last_fired_json")
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val listSerializer = ListSerializer(AutoRule.serializer())
    private val mapSerializer = MapSerializer(String.serializer(), Long.serializer())

    val rules: Flow<List<AutoRule>> = context.autoRulesDataStore.data.map { prefs ->
        prefs[rulesKey]?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() } ?: emptyList()
    }

    suspend fun rulesOnce(): List<AutoRule> = rules.first()

    suspend fun enabledOnce(): List<AutoRule> = rulesOnce().filter { it.enabled }

    suspend fun upsert(rule: AutoRule) {
        context.autoRulesDataStore.edit { prefs ->
            val current = prefs[rulesKey]
                ?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() }
                ?: emptyList()
            prefs[rulesKey] = json.encodeToString(listSerializer, current.filterNot { it.id == rule.id } + rule)
        }
    }

    suspend fun setEnabled(id: String, enabled: Boolean) {
        context.autoRulesDataStore.edit { prefs ->
            val current = prefs[rulesKey]
                ?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() }
                ?: return@edit
            prefs[rulesKey] = json.encodeToString(listSerializer, current.map {
                if (it.id == id) it.copy(enabled = enabled) else it
            })
        }
    }

    suspend fun delete(id: String) {
        context.autoRulesDataStore.edit { prefs ->
            val current = prefs[rulesKey]
                ?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() }
                ?: return@edit
            prefs[rulesKey] = json.encodeToString(listSerializer, current.filterNot { it.id == id })
        }
    }

    suspend fun lastFiredOnce(): Map<String, Long> {
        val raw = context.autoRulesDataStore.data.first()[lastFiredKey] ?: return emptyMap()
        return runCatching { json.decodeFromString(mapSerializer, raw) }.getOrDefault(emptyMap())
    }

    suspend fun markFired(id: String) {
        context.autoRulesDataStore.edit { prefs ->
            val current = prefs[lastFiredKey]
                ?.let { runCatching { json.decodeFromString(mapSerializer, it) }.getOrNull() }
                ?: emptyMap()
            prefs[lastFiredKey] = json.encodeToString(mapSerializer, current + (id to System.currentTimeMillis()))
        }
    }
}
