package com.freesystemdoctor.android.data.saf

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.safDataStore: DataStore<Preferences> by preferencesDataStore(name = "fsd_saf")

/** Persists the user-granted Storage Access Framework tree URI across sessions. */
class SafTreeStore(private val context: Context) {

    private val key = stringPreferencesKey("tree_uri")
    private val androidMediaKey = stringPreferencesKey("android_media_tree_uri")
    private val backupKey = stringPreferencesKey("backup_tree_uri")

    val treeUri: Flow<Uri?> = context.safDataStore.data.map { prefs ->
        prefs[key]?.let { Uri.parse(it) }
    }

    val androidMediaTreeUri: Flow<Uri?> = context.safDataStore.data.map { prefs ->
        prefs[androidMediaKey]?.let { Uri.parse(it) }
    }

    val backupTreeUri: Flow<Uri?> = context.safDataStore.data.map { prefs ->
        prefs[backupKey]?.let { Uri.parse(it) }
    }

    suspend fun current(): Uri? = treeUri.first()

    suspend fun persist(uri: Uri) {
        takePersistable(uri)
        context.safDataStore.edit { it[key] = uri.toString() }
    }

    suspend fun persistAndroidMedia(uri: Uri) {
        takePersistable(uri)
        context.safDataStore.edit { it[androidMediaKey] = uri.toString() }
    }

    suspend fun persistBackup(uri: Uri) {
        takePersistable(uri)
        context.safDataStore.edit { it[backupKey] = uri.toString() }
    }

    private fun takePersistable(uri: Uri) {
        runCatching {
            context.contentResolver.takePersistableUriPermission(
                uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION,
            )
        }
    }
}
