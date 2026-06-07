package com.freesystemdoctor.android.engine.battery

import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.pm.ApplicationInfo
import com.freesystemdoctor.android.core.permission.PermissionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

data class DrainEstimate(
    val packageName: String,
    val label: String,
    val foregroundMinutes: Long,
    val weight: Double,
) {
    val scaledScore: Double get() = foregroundMinutes * weight
}

/**
 * Honest battery-drain estimate. Real per-app mAh requires `BatteryStatsManager`,
 * which most OEMs deny outside system apps — so we report foreground-time + a
 * category weight and label it clearly as an estimate in the UI. No fake mAh.
 *
 * Weight buckets are intentionally coarse (1.0 / 1.5 / 2.0 / 2.5) to avoid
 * implying false precision.
 */
class BatteryDrainEngine(
    private val context: Context,
    private val permissions: PermissionManager,
) {

    suspend fun compute(): List<DrainEstimate> = withContext(Dispatchers.IO) {
        if (!permissions.hasUsageAccess()) return@withContext emptyList()
        val usm = context.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
            ?: return@withContext emptyList()
        val now = System.currentTimeMillis()
        val start = now - TimeUnit.DAYS.toMillis(7)
        val stats = usm.queryAndAggregateUsageStats(start, now)
        val pm = context.packageManager
        stats.values.mapNotNull { s ->
            val pkg = s.packageName ?: return@mapNotNull null
            val info = runCatching { pm.getApplicationInfo(pkg, 0) }.getOrNull() ?: return@mapNotNull null
            val foregroundMin = TimeUnit.MILLISECONDS.toMinutes(s.totalTimeInForeground)
            if (foregroundMin <= 0) return@mapNotNull null
            val label = runCatching { pm.getApplicationLabel(info).toString() }.getOrDefault(pkg)
            DrainEstimate(pkg, label, foregroundMin, weightFor(info))
        }.sortedByDescending { it.scaledScore }.take(50)
    }

    private fun weightFor(info: ApplicationInfo): Double {
        // Higher weight for known battery-hungry categories.
        val cat = info.category
        return when (cat) {
            ApplicationInfo.CATEGORY_GAME -> 2.5
            ApplicationInfo.CATEGORY_VIDEO, ApplicationInfo.CATEGORY_AUDIO -> 2.0
            ApplicationInfo.CATEGORY_MAPS -> 2.0
            ApplicationInfo.CATEGORY_SOCIAL -> 1.5
            else -> 1.0
        }
    }
}
