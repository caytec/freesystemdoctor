package com.freesystemdoctor.android.engine.apps

import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.pm.PackageManager
import com.freesystemdoctor.android.core.permission.PermissionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

data class AppUsageItem(
    val packageName: String,
    val label: String,
    val totalForegroundMillis: Long,
    val lastUsed: Long,
)

/**
 * Screen-time / usage statistics over a recent window via UsageStatsManager.
 * Requires the PACKAGE_USAGE_STATS special access (handled by [PermissionManager]).
 */
class AppUsageEngine(
    private val context: Context,
    private val permissions: PermissionManager,
) {

    suspend fun usage(days: Int = 7): List<AppUsageItem> = withContext(Dispatchers.IO) {
        if (!permissions.hasUsageAccess()) return@withContext emptyList()
        val usm = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val pm = context.packageManager
        val end = System.currentTimeMillis()
        val start = end - TimeUnit.DAYS.toMillis(days.toLong())

        usm.queryAndAggregateUsageStats(start, end).values
            .filter { it.totalTimeInForeground > 0 }
            .mapNotNull { stat ->
                val label = runCatching {
                    pm.getApplicationLabel(pm.getApplicationInfo(stat.packageName, 0)).toString()
                }.getOrNull() ?: stat.packageName
                AppUsageItem(
                    packageName = stat.packageName,
                    label = label,
                    totalForegroundMillis = stat.totalTimeInForeground,
                    lastUsed = stat.lastTimeUsed,
                )
            }
            .sortedByDescending { it.totalForegroundMillis }
    }
}
