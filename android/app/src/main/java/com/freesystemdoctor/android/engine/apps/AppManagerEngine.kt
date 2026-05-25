package com.freesystemdoctor.android.engine.apps

import android.app.usage.StorageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Process
import android.os.storage.StorageManager
import android.provider.Settings
import com.freesystemdoctor.android.core.permission.PermissionManager
import com.freesystemdoctor.android.core.result.ScanProgress
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class AppListItem(
    val packageName: String,
    val label: String,
    val totalBytes: Long,
    val isSystem: Boolean,
)

enum class AppSort { SIZE, NAME }

class AppManagerEngine(
    private val context: Context,
    private val permissions: PermissionManager,
) {

    suspend fun listApps(
        includeSystem: Boolean,
        sort: AppSort,
        progress: (ScanProgress) -> Unit = {},
    ): List<AppListItem> = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val hasUsage = permissions.hasUsageAccess()
        val ssm = context.getSystemService(Context.STORAGE_STATS_SERVICE) as StorageStatsManager
        val user = Process.myUserHandle()
        val uuid = StorageManager.UUID_DEFAULT

        val apps = pm.getInstalledApplications(PackageManager.GET_META_DATA)
        val items = ArrayList<AppListItem>(apps.size)
        apps.forEachIndexed { index, app ->
            val isSystem = (app.flags and ApplicationInfo.FLAG_SYSTEM) != 0
            if (!includeSystem && isSystem) return@forEachIndexed
            progress(ScanProgress(index + 1, apps.size, app.packageName))
            val size = if (hasUsage) {
                runCatching { ssm.queryStatsForPackage(uuid, app.packageName, user) }
                    .getOrNull()
                    ?.let { it.appBytes + it.dataBytes + it.cacheBytes }
                    ?: 0L
            } else {
                0L
            }
            items += AppListItem(
                packageName = app.packageName,
                label = pm.getApplicationLabel(app).toString(),
                totalBytes = size,
                isSystem = isSystem,
            )
        }
        when (sort) {
            AppSort.SIZE -> items.sortedByDescending { it.totalBytes }
            AppSort.NAME -> items.sortedBy { it.label.lowercase() }
        }
    }

    /** Launches the system uninstall confirmation dialog. */
    fun uninstallIntent(packageName: String): Intent =
        Intent(Intent.ACTION_DELETE, Uri.parse("package:$packageName"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    /** Opens the app's detail settings page (user can Force stop / Clear cache there). */
    fun appDetailsIntent(packageName: String): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}
