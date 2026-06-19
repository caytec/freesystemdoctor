package com.freeandroiddoctor.android.engine.storage

import android.app.usage.StorageStatsManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Process
import android.os.UserHandle
import android.os.storage.StorageManager
import com.freeandroiddoctor.android.core.permission.PermissionManager
import com.freeandroiddoctor.android.core.result.ScanProgress
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class VolumeInfo(
    val totalBytes: Long,
    val freeBytes: Long,
) {
    val usedBytes: Long get() = (totalBytes - freeBytes).coerceAtLeast(0)
    val usedFraction: Float
        get() = if (totalBytes <= 0) 0f else (usedBytes.toFloat() / totalBytes).coerceIn(0f, 1f)
}

data class AppStorage(
    val packageName: String,
    val label: String,
    val appBytes: Long,
    val dataBytes: Long,
    val cacheBytes: Long,
    val isSystem: Boolean,
) {
    val totalBytes: Long get() = appBytes + dataBytes + cacheBytes
}

class StorageAnalyzerEngine(
    private val context: Context,
    private val permissions: PermissionManager,
) {

    /** Primary internal volume totals — no special permission required. */
    fun readPrimaryVolume(): VolumeInfo {
        val ssm = context.getSystemService(Context.STORAGE_STATS_SERVICE) as StorageStatsManager
        val uuid = StorageManager.UUID_DEFAULT
        return VolumeInfo(
            totalBytes = ssm.getTotalBytes(uuid),
            freeBytes = ssm.getFreeBytes(uuid),
        )
    }

    /**
     * Per-app storage breakdown. Requires Usage Access (PACKAGE_USAGE_STATS).
     * Returns an empty list if the permission has not been granted.
     */
    suspend fun readPerApp(
        includeSystem: Boolean = false,
        progress: (ScanProgress) -> Unit = {},
    ): List<AppStorage> = withContext(Dispatchers.IO) {
        if (!permissions.hasUsageAccess()) return@withContext emptyList()

        val pm = context.packageManager
        val ssm = context.getSystemService(Context.STORAGE_STATS_SERVICE) as StorageStatsManager
        val user: UserHandle = Process.myUserHandle()
        val uuid = StorageManager.UUID_DEFAULT

        val apps = pm.getInstalledApplications(PackageManager.GET_META_DATA)
        val result = ArrayList<AppStorage>(apps.size)
        apps.forEachIndexed { index, app ->
            val isSystem = (app.flags and ApplicationInfo.FLAG_SYSTEM) != 0
            if (!includeSystem && isSystem) return@forEachIndexed
            progress(ScanProgress(index + 1, apps.size, app.packageName))
            runCatching {
                val stats = ssm.queryStatsForPackage(uuid, app.packageName, user)
                result += AppStorage(
                    packageName = app.packageName,
                    label = pm.getApplicationLabel(app).toString(),
                    appBytes = stats.appBytes,
                    dataBytes = stats.dataBytes,
                    cacheBytes = stats.cacheBytes,
                    isSystem = isSystem,
                )
            }
        }
        result.sortedByDescending { it.totalBytes }
    }
}
