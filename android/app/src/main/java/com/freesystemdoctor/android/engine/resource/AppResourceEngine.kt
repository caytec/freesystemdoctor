package com.freesystemdoctor.android.engine.resource

import android.content.Context
import com.freesystemdoctor.android.core.permission.PermissionManager
import com.freesystemdoctor.android.engine.apps.AppManagerEngine
import com.freesystemdoctor.android.engine.apps.AppSort
import com.freesystemdoctor.android.engine.apps.AppUsageEngine
import com.freesystemdoctor.android.engine.network.DataUsageEngine
import com.freesystemdoctor.android.engine.storage.StorageAnalyzerEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit
import kotlin.math.ln
import kotlin.math.max

data class AppResourceRow(
    val packageName: String,
    val label: String,
    val storageBytes: Long,
    val cacheBytes: Long,
    val data30dBytes: Long,
    val screenTime7dMillis: Long,
    val lastUsed: Long,
    val isSystem: Boolean,
    /** 0..100 — higher = more likely candidate to remove or restrict. */
    val score: Int,
)

data class AppResourceReport(
    val rows: List<AppResourceRow>,
    val needsUsageAccess: Boolean,
)

/**
 * Cross-cutting "cost" report: joins storage, cache, 30d data, 7d screen time and last-used
 * from four existing engines and produces a single 0..100 score per app. High score = good
 * candidate for review (think uninstall / restrict background / clear cache).
 *
 * Score formula:
 *   raw = w1·log(storageMB+1) + w2·log(cacheMB+1) + w3·log(data30dMB+1)
 *       - w4·log(screenTime7dMin+1) + w5·log(stalenessDays+1)
 * (log keeps weights interpretable across orders-of-magnitude differences between rows.)
 * The raw score is then linearly mapped 0..100 by min/max within the report.
 *
 * **Honest disclaimer** (surfaced in UI): the score is a heuristic; a high value does NOT
 * automatically mean the app is removable — some background utilities (sync agents,
 * IMEs, password managers) legitimately have no foreground screen time.
 */
class AppResourceEngine(
    private val context: Context,
    private val permissions: PermissionManager,
    private val appManager: AppManagerEngine,
    private val storage: StorageAnalyzerEngine,
    private val appUsage: AppUsageEngine,
    private val dataUsage: DataUsageEngine,
) {

    suspend fun report(includeSystem: Boolean = false, topN: Int = 50): AppResourceReport =
        withContext(Dispatchers.IO) {
            if (!permissions.hasUsageAccess()) {
                return@withContext AppResourceReport(emptyList(), needsUsageAccess = true)
            }
            coroutineScope {
                val storageDeferred = async { storage.readPerApp(includeSystem) }
                val appsDeferred = async { appManager.listApps(includeSystem, AppSort.SIZE) }
                val usageDeferred = async { appUsage.usage(7) }
                val dataDeferred = async { dataUsage.usage(30) }

                val storageByApp = storageDeferred.await().associateBy { it.packageName }
                val appsByPkg = appsDeferred.await().associateBy { it.packageName }
                val usageByPkg = usageDeferred.await().associateBy { it.packageName }
                val dataByPkg = dataDeferred.await()
                    .mapNotNull { item -> item.packageName?.let { it to item } }
                    .toMap()

                val now = System.currentTimeMillis()
                val keys = (storageByApp.keys + appsByPkg.keys + usageByPkg.keys + dataByPkg.keys)
                    .filter { it != context.packageName }

                val raw = keys.mapNotNull { pkg ->
                    val app = appsByPkg[pkg] ?: return@mapNotNull null
                    val st = storageByApp[pkg]
                    val use = usageByPkg[pkg]
                    val dt = dataByPkg[pkg]

                    val storageBytes = st?.totalBytes ?: app.totalBytes
                    val cacheBytes = st?.cacheBytes ?: 0L
                    val dataBytes = dt?.totalBytes ?: 0L
                    val screenMillis = use?.totalForegroundMillis ?: 0L
                    val lastUsed = use?.lastUsed ?: 0L

                    val storageMB = storageBytes / 1_000_000.0
                    val cacheMB = cacheBytes / 1_000_000.0
                    val dataMB = dataBytes / 1_000_000.0
                    val screenMin = screenMillis / 60_000.0
                    val stalenessDays = if (lastUsed <= 0) 365.0
                    else max(0.0, (now - lastUsed) / TimeUnit.DAYS.toMillis(1).toDouble())

                    val rawScore =
                        W_STORAGE * ln(storageMB + 1) +
                        W_CACHE * ln(cacheMB + 1) +
                        W_DATA * ln(dataMB + 1) -
                        W_SCREEN * ln(screenMin + 1) +
                        W_STALENESS * ln(stalenessDays + 1)

                    AppResourceRow(
                        packageName = pkg,
                        label = app.label,
                        storageBytes = storageBytes,
                        cacheBytes = cacheBytes,
                        data30dBytes = dataBytes,
                        screenTime7dMillis = screenMillis,
                        lastUsed = lastUsed,
                        isSystem = app.isSystem,
                        score = rawScore.toInt(), // temp; remapped below
                    ).let { it to rawScore }
                }

                val maxRaw = raw.maxOfOrNull { it.second } ?: 0.0
                val minRaw = raw.minOfOrNull { it.second } ?: 0.0
                val span = (maxRaw - minRaw).coerceAtLeast(1e-6)

                val rows = raw.map { (row, rawScore) ->
                    val normalized = ((rawScore - minRaw) / span * 100.0).toInt().coerceIn(0, 100)
                    row.copy(score = normalized)
                }
                    .sortedByDescending { it.score }
                    .take(topN)

                AppResourceReport(rows, needsUsageAccess = false)
            }
        }

    private companion object {
        const val W_STORAGE = 1.2
        const val W_CACHE = 0.6
        const val W_DATA = 0.9
        const val W_SCREEN = 1.5
        const val W_STALENESS = 1.0
    }
}
