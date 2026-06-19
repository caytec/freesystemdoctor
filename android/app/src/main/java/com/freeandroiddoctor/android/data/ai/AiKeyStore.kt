package com.freeandroiddoctor.android.data.ai

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** Stores the user-supplied AI API key encrypted at rest. */
class AiKeyStore(context: Context) {

    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "fsd_secure_keys",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun getApiKey(): String? = prefs.getString(KEY_API, null)?.takeIf { it.isNotBlank() }

    fun setApiKey(key: String) {
        prefs.edit().putString(KEY_API, key.trim()).apply()
    }

    fun clear() {
        prefs.edit().remove(KEY_API).apply()
    }

    fun hasKey(): Boolean = getApiKey() != null

    private companion object {
        const val KEY_API = "api_key"
    }
}
