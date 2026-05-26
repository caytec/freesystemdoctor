package com.freesystemdoctor.android.engine.contacts

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Environment
import android.provider.ContactsContract
import android.provider.MediaStore
import androidx.core.content.ContextCompat
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
 * Detects likely duplicate contacts and exports all contacts to a vCard (.vcf) file
 * in Downloads. Requires READ_CONTACTS (a sensitive permission, gated behind advanced mode).
 * Duplicates are surfaced for review only — merging happens in the system Contacts app.
 */
class ContactsEngine(private val context: Context) {

    fun hasPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) ==
            PackageManager.PERMISSION_GRANTED

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

    suspend fun exportVCard(): ContactsExportResult = withContext(Dispatchers.IO) {
        if (!hasPermission()) {
            return@withContext ContactsExportResult(false, "", error = "missing_permission")
        }
        val fileName = "contacts_${System.currentTimeMillis()}.vcf"
        runCatching {
            val lookupKeys = ArrayList<String>()
            context.contentResolver.query(
                ContactsContract.Contacts.CONTENT_URI,
                arrayOf(ContactsContract.Contacts.LOOKUP_KEY),
                null, null, null,
            )?.use { c ->
                val keyCol = c.getColumnIndexOrThrow(ContactsContract.Contacts.LOOKUP_KEY)
                while (c.moveToNext()) c.getString(keyCol)?.let(lookupKeys::add)
            }
            if (lookupKeys.isEmpty()) error("no_contacts")

            val vcardBytes = StringBuilder()
            lookupKeys.chunked(50).forEach { chunk ->
                val uri = ContactsContract.Contacts.CONTENT_MULTI_VCARD_URI.buildUpon()
                    .appendEncodedPath(chunk.joinToString(":")).build()
                context.contentResolver.openInputStream(uri)?.use {
                    vcardBytes.append(it.readBytes().toString(Charsets.UTF_8))
                }
            }
            writeToDownloads(fileName, "text/vcard", vcardBytes.toString().toByteArray())
            ContactsExportResult(true, fileName, lookupKeys.size)
        }.getOrElse { ContactsExportResult(false, fileName, error = it.message) }
    }

    private fun writeToDownloads(name: String, mime: String, bytes: ByteArray) {
        val resolver = context.contentResolver
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, name)
                put(MediaStore.Downloads.MIME_TYPE, mime)
                put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: error("insert_failed")
            resolver.openOutputStream(uri)?.use { it.write(bytes) }
            values.clear()
            values.put(MediaStore.Downloads.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        } else {
            @Suppress("DEPRECATION")
            val dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
            java.io.File(dir, name).outputStream().use { it.write(bytes) }
        }
    }
}
