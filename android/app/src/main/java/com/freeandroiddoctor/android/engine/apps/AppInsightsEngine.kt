package com.freeandroiddoctor.android.engine.apps

import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import com.freeandroiddoctor.android.core.permission.PermissionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.Calendar
import java.util.concurrent.TimeUnit

data class DailyUsage(val dayLabel: String, val foregroundMillis: Long)

data class AppEvent(
    val packageName: String,
    val label: String,
    val timestamp: Long,
    val isInstall: Boolean,
)

data class HiddenApp(
    val packageName: String,
    val label: String,
    val installedAt: Long,
)

data class InsightsReport(
    val weeklyTotalMillis: Long,
    val perDay: List<DailyUsage>,
    val recentlyInstalled: List<AppEvent>,
    val hiddenApps: List<HiddenApp>,
)

/**
 * Cross-cutting view of how the user actually uses their device: a 7-day usage trend, the
 * latest installs/updates, and apps with no launcher entry (often pre-installed bloat or
 * background-only utilities). All data is read locally; nothing is exported.
 */
class AppInsightsEngine(
    private val context: Context,
    private val permissions: PermissionManager,
) {

    suspend fun report(): InsightsReport = withContext(Dispatchers.IO) {
        val perDay = if (permissions.hasUsageAccess()) weeklyUsage() else emptyList()
        InsightsReport(
            weeklyTotalMillis = perDay.sumOf { it.foregroundMillis },
            perDay = perDay,
            recentlyInstalled = recentlyTouched(limit = 8),
            hiddenApps = hiddenApps(limit = 16),
        )
    }

    private fun weeklyUsage(): List<DailyUsage> {
        val usm = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val end = System.currentTimeMillis()
        val cal = Calendar.getInstance().apply {
            timeInMillis = end
            set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
            add(Calendar.DAY_OF_YEAR, -6)
        }
        val days = mutableListOf<DailyUsage>()
        repeat(7) {
            val dayStart = cal.timeInMillis
            cal.add(Calendar.DAY_OF_YEAR, 1)
            val dayEnd = cal.timeInMillis.coerceAtMost(end)
            val total = usm.queryAndAggregateUsageStats(dayStart, dayEnd)
                .values.sumOf { it.totalTimeInForeground }
            val label = SHORT_DAYS[(Calendar.getInstance().apply { timeInMillis = dayStart }
                .get(Calendar.DAY_OF_WEEK) + 5) % 7]
            days += DailyUsage(label, total)
        }
        return days
    }

    private fun recentlyTouched(limit: Int): List<AppEvent> {
        val pm = context.packageManager
        val cutoff = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(30)
        return pm.getInstalledPackages(0)
            .asSequence()
            .filter { it.applicationInfo != null && it.lastUpdateTime >= cutoff }
            .map { pkg ->
                val label = runCatching { pm.getApplicationLabel(pkg.applicationInfo!!).toString() }
                    .getOrDefault(pkg.packageName)
                AppEvent(
                    packageName = pkg.packageName,
                    label = label,
                    timestamp = pkg.lastUpdateTime,
                    isInstall = pkg.firstInstallTime == pkg.lastUpdateTime,
                )
            }
            .sortedByDescending { it.timestamp }
            .take(limit)
            .toList()
    }

    private fun hiddenApps(limit: Int): List<HiddenApp> {
        val pm = context.packageManager
        val launchable = pm.queryIntentActivities(
            Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER),
            0,
        ).mapTo(HashSet()) { it.activityInfo.packageName }

        return pm.getInstalledPackages(0)
            .asSequence()
            .filter { pkg ->
                val info = pkg.applicationInfo ?: return@filter false
                val isUser = (info.flags and android.content.pm.ApplicationInfo.FLAG_SYSTEM) == 0
                isUser && pkg.packageName !in launchable && pkg.packageName != context.packageName
            }
            .map { pkg ->
                val label = runCatching { pm.getApplicationLabel(pkg.applicationInfo!!).toString() }
                    .getOrDefault(pkg.packageName)
                HiddenApp(pkg.packageName, label, pkg.firstInstallTime)
            }
            .sortedByDescending { it.installedAt }
            .take(limit)
            .toList()
    }

    private companion object {
        val SHORT_DAYS = arrayOf("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    }
}
