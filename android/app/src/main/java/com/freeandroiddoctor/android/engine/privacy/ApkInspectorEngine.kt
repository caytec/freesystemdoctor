package com.freeandroiddoctor.android.engine.privacy

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.content.pm.PermissionInfo
import android.net.Uri
import androidx.core.content.pm.PackageInfoCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

data class ApkInspection(
    val label: String,
    val packageName: String,
    val versionName: String,
    val versionCode: Long,
    val minSdk: Int,
    val targetSdk: Int,
    val sizeBytes: Long,
    val dangerousPermissions: List<String>,
    val trackers: List<TrackerSignature>,
    val alreadyInstalled: Boolean,
    /** Set when the installed copy has a different signing certificate. */
    val signatureMismatch: Boolean,
    val debugSigned: Boolean,
)

/**
 * Inspects an APK file the user picked — BEFORE it is installed.
 *
 * Sideloading is normal for this audience (the app itself ships as an APK), yet nothing on
 * the market lets you see what is inside an installer first. This reads the archive's
 * manifest locally via [PackageManager.getPackageArchiveInfo] and reports the permissions
 * it will ask for, the tracking SDKs it embeds ([TrackerDb]), whether it is debug-signed,
 * and — importantly — whether it would REPLACE an installed app with a different signing
 * certificate, which is the classic malicious-update pattern.
 *
 * The APK is never installed, never uploaded, and the temporary copy is deleted afterwards.
 */
class ApkInspectorEngine(private val context: Context) {

    suspend fun inspect(source: Uri): ApkInspection? = withContext(Dispatchers.IO) {
        // getPackageArchiveInfo needs a real file path, so stream the picked
        // content:// Uri into our cache first, then always clean it up.
        val temp = File(context.cacheDir, "inspect_${System.currentTimeMillis()}.apk")
        try {
            context.contentResolver.openInputStream(source)?.use { input ->
                temp.outputStream().use { output -> input.copyTo(output) }
            } ?: return@withContext null

            val pm = context.packageManager
            val info = pm.getPackageArchiveInfo(temp.absolutePath, ARCHIVE_FLAGS)
                ?: return@withContext null
            // sourceDir must point at the archive for loadLabel to resolve resources.
            info.applicationInfo?.apply {
                sourceDir = temp.absolutePath
                publicSourceDir = temp.absolutePath
            }

            build(pm, info, temp.length())
        } finally {
            temp.delete()
        }
    }

    private fun build(pm: PackageManager, info: PackageInfo, sizeBytes: Long): ApkInspection {
        val appInfo = info.applicationInfo
        val label = appInfo?.let { runCatching { pm.getApplicationLabel(it).toString() }.getOrNull() }
            ?: info.packageName

        val dangerous = (info.requestedPermissions ?: emptyArray())
            .filter { isDangerous(pm, it) }
            .map { humanLabel(pm, it) }
            .sorted()

        val installed = runCatching { pm.getPackageInfo(info.packageName, 0) }.getOrNull()

        return ApkInspection(
            label = label,
            packageName = info.packageName,
            versionName = info.versionName.orEmpty(),
            versionCode = PackageInfoCompat.getLongVersionCode(info),
            minSdk = appInfo?.minSdkVersion ?: 0,
            targetSdk = appInfo?.targetSdkVersion ?: 0,
            sizeBytes = sizeBytes,
            dangerousPermissions = dangerous,
            trackers = detectTrackers(info),
            alreadyInstalled = installed != null,
            signatureMismatch = installed != null && signaturesDiffer(pm, info.packageName),
            debugSigned = appInfo != null &&
                (appInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0,
        )
    }

    private fun detectTrackers(info: PackageInfo): List<TrackerSignature> {
        val names = sequence {
            info.activities?.forEach { yield(it.name) }
            info.services?.forEach { yield(it.name) }
            info.receivers?.forEach { yield(it.name) }
            info.providers?.forEach { yield(it.name) }
        }
        val found = LinkedHashSet<TrackerSignature>()
        for (name in names) {
            if (name == null) continue
            for ((prefix, signature) in TrackerDb.byPrefix) {
                if (name.startsWith(prefix)) found += signature
            }
        }
        return found.toList().sortedBy { it.name }
    }

    /**
     * True when the installed app is signed by a different certificate than the archive —
     * Android would refuse the update, and it usually means the file is not a genuine
     * update of what you already have.
     */
    private fun signaturesDiffer(pm: PackageManager, pkg: String): Boolean = runCatching {
        // A mismatch is exactly what checkSignatures reports for same-name/different-cert.
        pm.checkSignatures(pkg, context.packageName) == PackageManager.SIGNATURE_NO_MATCH &&
            pkg != context.packageName
    }.getOrDefault(false)

    private val dangerousCache = HashMap<String, Boolean>()

    private fun isDangerous(pm: PackageManager, permission: String): Boolean =
        dangerousCache.getOrPut(permission) {
            runCatching {
                @Suppress("DEPRECATION")
                val level = pm.getPermissionInfo(permission, 0).protectionLevel
                (level and PermissionInfo.PROTECTION_MASK_BASE) == PermissionInfo.PROTECTION_DANGEROUS
            }.getOrDefault(false)
        }

    private fun humanLabel(pm: PackageManager, permission: String): String = runCatching {
        pm.getPermissionInfo(permission, 0).loadLabel(pm).toString()
            .replaceFirstChar { it.uppercase() }
    }.getOrElse {
        permission.substringAfterLast('.').replace('_', ' ').lowercase()
            .replaceFirstChar { it.uppercase() }
    }

    private companion object {
        const val ARCHIVE_FLAGS = PackageManager.GET_PERMISSIONS or
            PackageManager.GET_ACTIVITIES or
            PackageManager.GET_SERVICES or
            PackageManager.GET_RECEIVERS or
            PackageManager.GET_PROVIDERS
    }
}
