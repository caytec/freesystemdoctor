package com.freeandroiddoctor.android.data.watchdog

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.serialization.Serializable
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json

private val Context.watchdogDataStore: DataStore<Preferences> by
    preferencesDataStore(name = "fsd_perm_watchdog")

/** Point-in-time snapshot of one app's granted dangerous permissions. */
@Serializable
data class AppPermSnapshot(
    val pkg: String,
    val label: String,
    val versionCode: Long,
    val grantedDangerous: List<String>,
)

/**
 * Persists the last permission baseline so the watchdog can diff "what changed
 * since last check" over time. Stored locally as JSON; never leaves the device.
 */
class PermissionSnapshotStore(private val context: Context) {

    private val baselineKey = stringPreferencesKey("baseline_json")
    private val lastScanKey = longPreferencesKey("last_scan_at")
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val serializer = ListSerializer(AppPermSnapshot.serializer())

    /** Returns the stored baseline keyed by package, or empty if never scanned. */
    suspend fun baseline(): Map<String, AppPermSnapshot> {
        val raw = context.watchdogDataStore.data.first()[baselineKey] ?: return emptyMap()
        return runCatching { json.decodeFromString(serializer, raw) }
            .getOrDefault(emptyList())
            .associateBy { it.pkg }
    }

    suspend fun hasBaseline(): Boolean =
        context.watchdogDataStore.data.first()[baselineKey] != null

    suspend fun lastScanAt(): Long =
        context.watchdogDataStore.data.first()[lastScanKey] ?: 0L

    suspend fun save(snapshots: Collection<AppPermSnapshot>) {
        context.watchdogDataStore.edit { prefs ->
            prefs[baselineKey] = json.encodeToString(serializer, snapshots.toList())
            prefs[lastScanKey] = System.currentTimeMillis()
        }
    }
}
