package com.freeandroiddoctor.android.data.privacy

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

private val Context.privacyDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_privacy")

/** Built-in or user-saved profile that describes a "harden the device" preset. */
@Serializable
data class PrivacyProfile(
    val id: String,
    val labelKey: String,
    val builtIn: Boolean = false,
    val forbidLocation: Boolean = false,
    val forbidContacts: Boolean = false,
    val forbidSms: Boolean = false,
    val forbidCallLog: Boolean = false,
    val forbidMicrophone: Boolean = false,
    val forbidCamera: Boolean = false,
    val forbidBackgroundLocation: Boolean = true,
    val clearClipboard: Boolean = true,
    val suggestPrivateDns: Boolean = false,
) {
    fun forbidsPermission(perm: String): Boolean = when (perm) {
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION" -> forbidLocation
        "android.permission.ACCESS_BACKGROUND_LOCATION" -> forbidBackgroundLocation || forbidLocation
        "android.permission.READ_CONTACTS",
        "android.permission.WRITE_CONTACTS" -> forbidContacts
        "android.permission.READ_SMS",
        "android.permission.SEND_SMS",
        "android.permission.RECEIVE_SMS" -> forbidSms
        "android.permission.READ_CALL_LOG",
        "android.permission.WRITE_CALL_LOG" -> forbidCallLog
        "android.permission.RECORD_AUDIO" -> forbidMicrophone
        "android.permission.CAMERA" -> forbidCamera
        else -> false
    }
}

class PrivacyProfileStore(private val context: Context) {

    private val customKey = stringPreferencesKey("custom_profiles_json")
    private val activeKey = stringPreferencesKey("active_profile_id")
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val listSerializer = ListSerializer(PrivacyProfile.serializer())

    val activeProfileId: Flow<String?> = context.privacyDataStore.data.map { it[activeKey] }

    val customProfiles: Flow<List<PrivacyProfile>> = context.privacyDataStore.data.map { prefs ->
        val raw = prefs[customKey] ?: return@map emptyList()
        runCatching { json.decodeFromString(listSerializer, raw) }.getOrDefault(emptyList())
    }

    suspend fun setActiveProfile(id: String?) {
        context.privacyDataStore.edit { prefs ->
            if (id == null) prefs.remove(activeKey) else prefs[activeKey] = id
        }
    }

    suspend fun saveCustom(profile: PrivacyProfile) {
        context.privacyDataStore.edit { prefs ->
            val current = prefs[customKey]
                ?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() }
                ?: emptyList()
            val replaced = current.filterNot { it.id == profile.id } + profile
            prefs[customKey] = json.encodeToString(listSerializer, replaced)
        }
    }

    suspend fun deleteCustom(id: String) {
        context.privacyDataStore.edit { prefs ->
            val current = prefs[customKey]
                ?.let { runCatching { json.decodeFromString(listSerializer, it) }.getOrNull() }
                ?: return@edit
            prefs[customKey] = json.encodeToString(listSerializer, current.filterNot { it.id == id })
        }
    }

    suspend fun allProfilesOnce(): List<PrivacyProfile> =
        BuiltInProfiles.all + customProfiles.first()
}

object BuiltInProfiles {

    val balanced = PrivacyProfile(
        id = "balanced",
        labelKey = "privacy_profile_balanced",
        builtIn = true,
        forbidBackgroundLocation = true,
        clearClipboard = true,
    )

    val strict = PrivacyProfile(
        id = "strict",
        labelKey = "privacy_profile_strict",
        builtIn = true,
        forbidLocation = true,
        forbidContacts = true,
        forbidSms = true,
        forbidCallLog = true,
        forbidMicrophone = true,
        forbidCamera = false,
        forbidBackgroundLocation = true,
        clearClipboard = true,
        suggestPrivateDns = true,
    )

    val game = PrivacyProfile(
        id = "game",
        labelKey = "privacy_profile_game",
        builtIn = true,
        forbidBackgroundLocation = true,
        clearClipboard = false,
    )

    val all = listOf(balanced, strict, game)
}
