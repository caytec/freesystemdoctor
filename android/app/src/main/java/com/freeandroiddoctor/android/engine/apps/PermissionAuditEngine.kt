package com.freeandroiddoctor.android.engine.apps

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class AuditedApp(
    val packageName: String,
    val label: String,
    val grantedDangerous: List<String>,
    val isSystem: Boolean,
) {
    val riskScore: Int get() = grantedDangerous.size
}

/**
 * Audits which "dangerous" runtime permissions each app has been granted.
 * Uses PackageManager.GET_PERMISSIONS — no special access required.
 */
class PermissionAuditEngine(private val context: Context) {

    suspend fun audit(includeSystem: Boolean = false): List<AuditedApp> =
        withContext(Dispatchers.IO) {
            val pm = context.packageManager
            // Guard against TransactionTooLargeException on devices with many apps.
            val packages = runCatching {
                pm.getInstalledPackages(PackageManager.GET_PERMISSIONS)
            }.getOrDefault(emptyList())
            packages.mapNotNull { info ->
                val appInfo = info.applicationInfo ?: return@mapNotNull null
                val isSystem = (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0
                if (!includeSystem && isSystem) return@mapNotNull null
                val granted = grantedDangerous(pm, info)
                if (granted.isEmpty()) return@mapNotNull null
                AuditedApp(
                    packageName = info.packageName,
                    label = runCatching { pm.getApplicationLabel(appInfo).toString() }
                        .getOrNull() ?: info.packageName,
                    grantedDangerous = granted,
                    isSystem = isSystem,
                )
            }.sortedByDescending { it.riskScore }
        }

    private fun grantedDangerous(pm: PackageManager, info: PackageInfo): List<String> {
        val names = info.requestedPermissions ?: return emptyList()
        val flags = info.requestedPermissionsFlags
        val out = ArrayList<String>()
        names.forEachIndexed { i, perm ->
            val isGranted = flags != null &&
                i < flags.size &&
                (flags[i] and PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0
            if (isGranted && perm in DANGEROUS) {
                out += perm.substringAfterLast('.')
            }
        }
        return out.distinct().sorted()
    }

    private companion object {
        val DANGEROUS = setOf(
            "android.permission.CAMERA",
            "android.permission.RECORD_AUDIO",
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION",
            "android.permission.ACCESS_BACKGROUND_LOCATION",
            "android.permission.READ_CONTACTS",
            "android.permission.WRITE_CONTACTS",
            "android.permission.READ_SMS",
            "android.permission.SEND_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.READ_CALL_LOG",
            "android.permission.WRITE_CALL_LOG",
            "android.permission.READ_PHONE_STATE",
            "android.permission.CALL_PHONE",
            "android.permission.READ_CALENDAR",
            "android.permission.WRITE_CALENDAR",
            "android.permission.BODY_SENSORS",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_IMAGES",
            "android.permission.READ_MEDIA_VIDEO",
            "android.permission.READ_MEDIA_AUDIO",
        )
    }
}
