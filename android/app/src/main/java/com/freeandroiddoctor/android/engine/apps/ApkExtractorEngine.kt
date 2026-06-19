package com.freeandroiddoctor.android.engine.apps

import android.content.ContentValues
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

data class BackupableApp(
    val packageName: String,
    val label: String,
    val versionName: String,
    val apkSizeBytes: Long,
    val sourceDir: String,
)

data class ApkExtractResult(val success: Boolean, val displayName: String, val error: String? = null)

/**
 * Lists installed apps and extracts their base APK into the public Downloads
 * collection via MediaStore (no WRITE_EXTERNAL_STORAGE needed on API 29+).
 */
class ApkExtractorEngine(private val context: Context) {

    suspend fun listApps(includeSystem: Boolean = false): List<BackupableApp> =
        withContext(Dispatchers.IO) {
            val pm = context.packageManager
            pm.getInstalledApplications(0).mapNotNull { app ->
                val isSystem = (app.flags and ApplicationInfo.FLAG_SYSTEM) != 0
                if (!includeSystem && isSystem) return@mapNotNull null
                val src = app.sourceDir ?: return@mapNotNull null
                val file = File(src)
                if (!file.exists()) return@mapNotNull null
                val pkgInfo = runCatching { pm.getPackageInfo(app.packageName, 0) }.getOrNull()
                BackupableApp(
                    packageName = app.packageName,
                    label = runCatching { pm.getApplicationLabel(app).toString() }
                        .getOrNull() ?: app.packageName,
                    versionName = pkgInfo?.versionName ?: "?",
                    apkSizeBytes = file.length(),
                    sourceDir = src,
                )
            }.sortedBy { it.label.lowercase() }
        }

    suspend fun extract(app: BackupableApp): ApkExtractResult = withContext(Dispatchers.IO) {
        val safeLabel = app.label.replace(Regex("[^A-Za-z0-9._-]"), "_")
        val fileName = "${safeLabel}_${app.versionName}.apk"
        runCatching {
            val source = File(app.sourceDir)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                    put(MediaStore.Downloads.MIME_TYPE, "application/vnd.android.package-archive")
                    put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                    put(MediaStore.Downloads.IS_PENDING, 1)
                }
                val resolver = context.contentResolver
                val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                    ?: error("insert_failed")
                resolver.openOutputStream(uri)?.use { out -> source.inputStream().use { it.copyTo(out) } }
                values.clear()
                values.put(MediaStore.Downloads.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            } else {
                @Suppress("DEPRECATION")
                val downloads =
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                val dest = File(downloads, fileName)
                source.inputStream().use { input -> dest.outputStream().use { input.copyTo(it) } }
            }
            ApkExtractResult(success = true, displayName = fileName)
        }.getOrElse {
            ApkExtractResult(success = false, displayName = fileName, error = it.message)
        }
    }
}
