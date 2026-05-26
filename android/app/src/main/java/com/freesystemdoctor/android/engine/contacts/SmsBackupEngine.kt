package com.freesystemdoctor.android.engine.contacts

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.provider.Telephony
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

data class SmsBackupResult(
    val success: Boolean,
    val fileName: String,
    val count: Int = 0,
    val error: String? = null,
)

/**
 * Exports SMS messages to a JSON file in Downloads. Requires READ_SMS (sensitive,
 * gated behind advanced mode). Read-only — nothing is modified or sent.
 */
class SmsBackupEngine(private val context: Context) {

    fun hasPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.READ_SMS) ==
            PackageManager.PERMISSION_GRANTED

    suspend fun export(): SmsBackupResult = withContext(Dispatchers.IO) {
        if (!hasPermission()) return@withContext SmsBackupResult(false, "", error = "missing_permission")
        val fileName = "sms_backup_${System.currentTimeMillis()}.json"
        runCatching {
            val array = JSONArray()
            context.contentResolver.query(
                Telephony.Sms.CONTENT_URI,
                arrayOf(
                    Telephony.Sms.ADDRESS,
                    Telephony.Sms.BODY,
                    Telephony.Sms.DATE,
                    Telephony.Sms.TYPE,
                ),
                null, null, "${Telephony.Sms.DATE} DESC",
            )?.use { c ->
                val addrCol = c.getColumnIndexOrThrow(Telephony.Sms.ADDRESS)
                val bodyCol = c.getColumnIndexOrThrow(Telephony.Sms.BODY)
                val dateCol = c.getColumnIndexOrThrow(Telephony.Sms.DATE)
                val typeCol = c.getColumnIndexOrThrow(Telephony.Sms.TYPE)
                while (c.moveToNext()) {
                    array.put(
                        JSONObject()
                            .put("address", c.getString(addrCol).orEmpty())
                            .put("body", c.getString(bodyCol).orEmpty())
                            .put("date", c.getLong(dateCol))
                            .put("type", c.getInt(typeCol)),
                    )
                }
            }
            writeToDownloads(fileName, array.toString())
            SmsBackupResult(true, fileName, array.length())
        }.getOrElse { SmsBackupResult(false, fileName, error = it.message) }
    }

    private fun writeToDownloads(name: String, content: String) {
        val resolver = context.contentResolver
        val bytes = content.toByteArray()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, name)
                put(MediaStore.Downloads.MIME_TYPE, "application/json")
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
