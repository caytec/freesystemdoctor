package com.freeandroiddoctor.android.engine.watchdog

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.content.pm.PermissionInfo
import androidx.core.content.pm.PackageInfoCompat
import com.freeandroiddoctor.android.data.watchdog.AppPermSnapshot
import com.freeandroiddoctor.android.data.watchdog.PermissionSnapshotStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlin.coroutines.coroutineContext

/** A permission change detected for one app since the last baseline. */
data class PermChange(
    val pkg: String,
    val label: String,
    /** Human-readable labels of newly-granted dangerous permissions. */
    val addedPermissions: List<String>,
    val versionBumped: Boolean,
    val isNewApp: Boolean,
)

data class WatchdogResult(
    val firstRun: Boolean,
    val changes: List<PermChange>,
    val scannedApps: Int,
)

/**
 * Temporal permission diff — the "permission-change watchdog". Snapshots every
 * app's granted dangerous permissions, then on later scans reports what changed:
 * "App X's update just added Location + Contacts access." No mainstream cleaner
 * does this over time; static point-in-time audits miss the moment a permission
 * quietly appears in an update. 100% on-device.
 */
class PermissionWatchdogEngine(
    private val context: Context,
    private val store: PermissionSnapshotStore,
) {

    /**
     * Scans installed apps and diffs against the stored baseline. On the very
     * first run it establishes the baseline and reports [WatchdogResult.firstRun]
     * = true with no changes. When [persist] is true the baseline is updated.
     */
    suspend fun scan(persist: Boolean = true): WatchdogResult = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val current = readSnapshots(pm)
        val baseline = store.baseline()
        val firstRun = !store.hasBaseline()

        val changes = if (firstRun) {
            emptyList()
        } else {
            val labelCache = HashMap<String, String>()
            current.values.mapNotNull { snap ->
                coroutineContext.ensureActive()
                val old = baseline[snap.pkg]
                when {
                    old == null -> {
                        // App installed since the last check — surface what it can access.
                        if (snap.grantedDangerous.isEmpty()) return@mapNotNull null
                        PermChange(
                            pkg = snap.pkg,
                            label = snap.label,
                            addedPermissions = snap.grantedDangerous.map { humanLabel(pm, it, labelCache) },
                            versionBumped = false,
                            isNewApp = true,
                        )
                    }
                    else -> {
                        val added = snap.grantedDangerous - old.grantedDangerous.toSet()
                        if (added.isEmpty()) return@mapNotNull null
                        PermChange(
                            pkg = snap.pkg,
                            label = snap.label,
                            addedPermissions = added.map { humanLabel(pm, it, labelCache) },
                            versionBumped = snap.versionCode != old.versionCode,
                            isNewApp = false,
                        )
                    }
                }
            }.sortedWith(
                compareByDescending<PermChange> { it.isNewApp }
                    .thenByDescending { it.addedPermissions.size },
            )
        }

        if (persist) store.save(current.values)
        WatchdogResult(firstRun = firstRun, changes = changes, scannedApps = current.size)
    }

    private fun readSnapshots(pm: PackageManager): Map<String, AppPermSnapshot> {
        val packages = runCatching {
            pm.getInstalledPackages(PackageManager.GET_PERMISSIONS)
        }.getOrDefault(emptyList())

        val result = HashMap<String, AppPermSnapshot>(packages.size)
        for (info in packages) {
            val appInfo = info.applicationInfo ?: continue
            // Skip system apps: their permissions are fixed by the OS and just noise.
            if ((appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0 &&
                (appInfo.flags and ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) == 0
            ) {
                continue
            }
            val granted = grantedDangerous(pm, info)
            result[info.packageName] = AppPermSnapshot(
                pkg = info.packageName,
                label = runCatching { appInfo.loadLabel(pm).toString() }
                    .getOrDefault(info.packageName),
                versionCode = PackageInfoCompat.getLongVersionCode(info),
                grantedDangerous = granted,
            )
        }
        return result
    }

    private fun grantedDangerous(pm: PackageManager, info: PackageInfo): List<String> {
        val names = info.requestedPermissions ?: return emptyList()
        val flags = info.requestedPermissionsFlags ?: return emptyList()
        val out = ArrayList<String>()
        for (i in names.indices) {
            val granted = i < flags.size &&
                (flags[i] and PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0
            if (granted && isDangerous(pm, names[i])) out += names[i]
        }
        return out.sorted()
    }

    private val dangerousCache = HashMap<String, Boolean>()

    private fun isDangerous(pm: PackageManager, permission: String): Boolean =
        dangerousCache.getOrPut(permission) {
            runCatching {
                @Suppress("DEPRECATION")
                val level = pm.getPermissionInfo(permission, 0).protectionLevel
                (level and PermissionInfo.PROTECTION_MASK_BASE) == PermissionInfo.PROTECTION_DANGEROUS
            }.getOrDefault(false)
        }

    private fun humanLabel(
        pm: PackageManager,
        permission: String,
        cache: MutableMap<String, String>,
    ): String = cache.getOrPut(permission) {
        runCatching {
            pm.getPermissionInfo(permission, 0).loadLabel(pm).toString()
                .replaceFirstChar { it.uppercase() }
        }.getOrElse {
            // Fallback: "android.permission.ACCESS_FINE_LOCATION" -> "Access fine location"
            permission.substringAfterLast('.')
                .replace('_', ' ')
                .lowercase()
                .replaceFirstChar { it.uppercase() }
        }
    }
}
