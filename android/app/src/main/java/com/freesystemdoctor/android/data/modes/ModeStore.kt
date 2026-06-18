package com.freesystemdoctor.android.data.modes

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
import kotlinx.serialization.json.Json

private val Context.modesDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_modes")

@Serializable
data class AppMode(
    val id: String,
    val labelKey: String,
    val builtIn: Boolean = false,
    val privacyProfileId: String? = null,
    val applyDarkTheme: Boolean? = null,
    val snoozeAllNotifications: Boolean = false,
    val pauseScheduledClean: Boolean = false,
    val lockedAppPackages: List<String> = emptyList(),
    val forceStopPackages: List<String> = emptyList(),
    val suggestPrivateDns: Boolean = false,
)

@Serializable
data class ModeSnapshot(
    val activeModeId: String,
    val priorDarkTheme: Boolean? = null,
    val priorScheduledClean: Boolean? = null,
    val activatedAt: Long = 0L,
)

class ModeStore(private val context: Context) {

    private val customKey = stringPreferencesKey("custom_modes_json")
    private val snapshotKey = stringPreferencesKey("active_snapshot_json")
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val listSerializer = ListSerializer(AppMode.serializer())
    private val snapshotSerializer = ModeSnapshot.serializer()

    val activeSnapshot: Flow<ModeSnapshot?> = context.modesDataStore.data.map { prefs ->
        prefs[snapshotKey]?.let { runCatching { json.decodeFromString(snapshotSerializer, it) }.getOrNull() }
    }

    val customModes: Flow<List<AppMode>> = context.modesDataStore.data.map { prefs ->
        prefs[customKey]?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() } ?: emptyList()
    }

    suspend fun activeSnapshotOnce(): ModeSnapshot? = activeSnapshot.first()

    suspend fun customModesOnce(): List<AppMode> = customModes.first()

    suspend fun allModesOnce(): List<AppMode> = BuiltInModes.all + customModesOnce()

    suspend fun setActiveSnapshot(snapshot: ModeSnapshot?) {
        context.modesDataStore.edit { prefs ->
            if (snapshot == null) prefs.remove(snapshotKey)
            else prefs[snapshotKey] = json.encodeToString(snapshotSerializer, snapshot)
        }
    }

    suspend fun saveCustom(mode: AppMode) {
        context.modesDataStore.edit { prefs ->
            val current = prefs[customKey]
                ?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() }
                ?: emptyList()
            prefs[customKey] = json.encodeToString(listSerializer, current.filterNot { it.id == mode.id } + mode)
        }
    }

    suspend fun deleteCustom(id: String) {
        context.modesDataStore.edit { prefs ->
            val current = prefs[customKey]
                ?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() }
                ?: return@edit
            prefs[customKey] = json.encodeToString(listSerializer, current.filterNot { it.id == id })
        }
    }
}

object BuiltInModes {

    val game = AppMode(
        id = "game",
        labelKey = "mode_game",
        builtIn = true,
        applyDarkTheme = true,
        snoozeAllNotifications = true,
        pauseScheduledClean = true,
        privacyProfileId = "game",
    )

    val travel = AppMode(
        id = "travel",
        labelKey = "mode_travel",
        builtIn = true,
        snoozeAllNotifications = false,
        privacyProfileId = "strict",
        suggestPrivateDns = true,
    )

    val focus = AppMode(
        id = "focus",
        labelKey = "mode_focus",
        builtIn = true,
        snoozeAllNotifications = true,
        pauseScheduledClean = false,
        privacyProfileId = "balanced",
    )

    val privacy = AppMode(
        id = "privacy",
        labelKey = "mode_privacy",
        builtIn = true,
        privacyProfileId = "strict",
        suggestPrivateDns = true,
    )

    val storageSaver = AppMode(
        id = "storage_saver",
        labelKey = "mode_storage_saver",
        builtIn = true,
        pauseScheduledClean = false,
    )

    val all = listOf(game, travel, focus, privacy, storageSaver)
}
