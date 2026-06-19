package com.freeandroiddoctor.android.engine.apps

import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import com.freeandroiddoctor.android.core.permission.PermissionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

data class RarelyUsedApp(
    val packageName: String,
    val label: String,
    val lastUsed: Long,
    val neverUsed: Boolean,
)

/**
 * Surfaces user-installed apps not opened within [thresholdDays].
 * Requires PACKAGE_USAGE_STATS; ignores system apps.
 */
class RarelyUsedEngine(
    private val context: Context,
    private val permissions: PermissionManager,
) {

    suspend fun rarelyUsed(thresholdDays: Int = 30): List<RarelyUsedApp> =
        withContext(Dispatchers.IO) {
            if (!permissions.hasUsageAccess()) return@withContext emptyList()
            val usm = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            val pm = context.packageManager
            val end = System.currentTimeMillis()
            val cutoff = end - TimeUnit.DAYS.toMillis(thresholdDays.toLong())
            val lookback = end - TimeUnit.DAYS.toMillis(365)

            val lastUsedByPkg = usm.queryAndAggregateUsageStats(lookback, end)
                .mapValues { it.value.lastTimeUsed }

            pm.getInstalledApplications(0)
                .filter { (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 }
                .filter { it.packageName != context.packageName }
                .mapNotNull { app ->
                    val last = lastUsedByPkg[app.packageName] ?: 0L
                    if (last > cutoff) return@mapNotNull null
                    RarelyUsedApp(
                        packageName = app.packageName,
                        label = runCatching { pm.getApplicationLabel(app).toString() }
                            .getOrNull() ?: app.packageName,
                        lastUsed = last,
                        neverUsed = last <= 0L,
                    )
                }
                .sortedBy { it.lastUsed }
        }
}
