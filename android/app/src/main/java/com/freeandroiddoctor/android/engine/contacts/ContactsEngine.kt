package com.freeandroiddoctor.android.engine.contacts

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.ContactsContract
import androidx.core.content.ContextCompat
import com.freeandroiddoctor.android.engine.cloudbackup.BackupCryptoEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class DuplicateContact(val displayName: String, val count: Int)

data class ContactsExportResult(
    val success: Boolean,
    val fileName: String,
    val count: Int = 0,
    val error: String? = null,
)

/**
 * Detects likely duplicate contacts and exports the address book as an
 * AES-256/GCM encrypted vCard archive to a destination the user picks
 * (Storage Access Framework). Requires READ_CONTACTS (sensitive, gated behind
 * advanced mode). Duplicates are surfaced for review only — merging happens in
 * the system Contacts app.
 *
 * The export is never written in plaintext to shared storage: the whole address
 * book in a world-readable Downloads file would be harvestable by any app with
 * file access.
 */
class ContactsEngine(
    private val context: Context,
    private val crypto: BackupCryptoEngine = BackupCryptoEngine(),
) {

    fun hasPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) ==
            PackageManager.PERMISSION_GRANTED

    fun suggestedFileName(): String = "contacts_${System.currentTimeMillis()}$EXTENSION"

    suspend fun findDuplicates(): List<DuplicateContact> = withContext(Dispatchers.IO) {
        if (!hasPermission()) return@withContext emptyList()
        val counts = HashMap<String, Int>()
        context.contentResolver.query(
            ContactsContract.Contacts.CONTENT_URI,
            arrayOf(ContactsContract.Contacts.DISPLAY_NAME),
            null, null, null,
        )?.use { c ->
            val nameCol = c.getColumnIndexOrThrow(ContactsContract.Contacts.DISPLAY_NAME)
            while (c.moveToNext()) {
                val name = c.getString(nameCol)?.trim().orEmpty()
                if (name.isNotBlank()) {
                    val key = name.lowercase()
                    counts[key] = (counts[key] ?: 0) + 1
                }
            }
        }
        counts.filter { it.value > 1 }
            .map { DuplicateContact(it.key.replaceFirstChar { ch -> ch.uppercase() }, it.value) }
            .sortedByDescending { it.count }
    }

    /**
     * Streams the vCard export into [target] (a `content://` Uri from
     * ACTION_CREATE_DOCUMENT), encrypted with [passphrase].
     */
    suspend fun exportEncrypted(target: Uri, passphrase: CharArray): ContactsExportResult =
        withContext(Dispatchers.IO) {
            if (!hasPermission()) {
                return@withContext ContactsExportResult(false, "", error = "missing_permission")
            }
            if (passphrase.isEmpty()) {
                return@withContext ContactsExportResult(false, "", error = "empty_passphrase")
            }
            runCatching {
                val lookupKeys = readLookupKeys()
                if (lookupKeys.isEmpty()) error("no_contacts")

                context.contentResolver.openOutputStream(target)?.use { raw ->
                    crypto.wrap(raw, passphrase).use { encrypted ->
                        // Stream chunk by chunk instead of building one big String:
                        // a large address book would otherwise sit in memory twice.
                        lookupKeys.chunked(CHUNK_SIZE).forEach { chunk ->
                            val uri = ContactsContract.Contacts.CONTENT_MULTI_VCARD_URI
                                .buildUpon()
                                .appendEncodedPath(chunk.joinToString(":"))
                                .build()
                            context.contentResolver.openInputStream(uri)?.use { input ->
                                input.copyTo(encrypted)
                            }
                        }
                    }
                } ?: error("open_failed")
                ContactsExportResult(true, target.lastPathSegment.orEmpty(), lookupKeys.size)
            }.getOrElse { ContactsExportResult(false, "", error = it.message) }
                .also { passphrase.fill(' ') }
        }

    private fun readLookupKeys(): List<String> {
        val lookupKeys = ArrayList<String>()
        context.contentResolver.query(
            ContactsContract.Contacts.CONTENT_URI,
            arrayOf(ContactsContract.Contacts.LOOKUP_KEY),
            null, null, null,
        )?.use { c ->
            val keyCol = c.getColumnIndexOrThrow(ContactsContract.Contacts.LOOKUP_KEY)
            while (c.moveToNext()) c.getString(keyCol)?.let(lookupKeys::add)
        }
        return lookupKeys
    }

    companion object {
        const val EXTENSION = ".fadenc"
        const val MIME_TYPE = "application/octet-stream"
        private const val CHUNK_SIZE = 50
    }
}
