package com.freesystemdoctor.android.data.cloudbackup

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Stores the user's cloud-backup passphrase locally in [EncryptedSharedPreferences] so the
 * scheduled worker can pick it up without re-prompting. The passphrase itself is the user's
 * choice; we never transmit it or compare hashes off-device.
 *
 * Users who don't want the auto-backup feature simply skip setting a stored passphrase —
 * the worker is then a no-op and they always type the passphrase manually.
 */
class CloudBackupKeyStore(private val context: Context) {

    private val prefs by lazy {
        val key = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "fsd_cloud_backup_key",
            key,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun read(): String? = prefs.getString(KEY, null)

    fun write(passphrase: String) {
        prefs.edit().putString(KEY, passphrase).apply()
    }

    fun clear() {
        prefs.edit().remove(KEY).apply()
    }

    private companion object { const val KEY = "passphrase" }
}
