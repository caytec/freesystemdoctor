package com.freesystemdoctor.android.engine.network

import android.app.usage.NetworkStats
import android.app.usage.NetworkStatsManager
import android.content.Context
import android.net.ConnectivityManager
import com.freesystemdoctor.android.core.permission.PermissionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

data class DataUsageItem(
    val label: String,
    val mobileBytes: Long,
    val wifiBytes: Long,
) {
    val totalBytes: Long get() = mobileBytes + wifiBytes
}

/**
 * Per-app mobile + Wi-Fi data usage over a recent window via NetworkStatsManager.
 * Querying other apps' UIDs requires the PACKAGE_USAGE_STATS special access.
 */
class DataUsageEngine(
    private val context: Context,
    private val permissions: PermissionManager,
) {

    suspend fun usage(days: Int = 30): List<DataUsageItem> = withContext(Dispatchers.IO) {
        if (!permissions.hasUsageAccess()) return@withContext emptyList()
        val nsm = context.getSystemService(Context.NETWORK_STATS_SERVICE) as NetworkStatsManager
        val pm = context.packageManager
        val end = System.currentTimeMillis()
        val start = end - TimeUnit.DAYS.toMillis(days.toLong())

        val mobile = bytesByUid(nsm, ConnectivityManager.TYPE_MOBILE, start, end)
        val wifi = bytesByUid(nsm, ConnectivityManager.TYPE_WIFI, start, end)

        val uids = (mobile.keys + wifi.keys)
        uids.mapNotNull { uid ->
            val label = labelForUid(pm, uid) ?: return@mapNotNull null
            val item = DataUsageItem(
                label = label,
                mobileBytes = mobile[uid] ?: 0L,
                wifiBytes = wifi[uid] ?: 0L,
            )
            if (item.totalBytes <= 0) null else item
        }.sortedByDescending { it.totalBytes }
    }

    private fun bytesByUid(
        nsm: NetworkStatsManager,
        networkType: Int,
        start: Long,
        end: Long,
    ): Map<Int, Long> {
        val result = HashMap<Int, Long>()
        val stats = runCatching {
            @Suppress("DEPRECATION")
            nsm.querySummary(networkType, null, start, end)
        }.getOrNull() ?: return result
        val bucket = NetworkStats.Bucket()
        while (stats.hasNextBucket()) {
            stats.getNextBucket(bucket)
            result[bucket.uid] = (result[bucket.uid] ?: 0L) + bucket.rxBytes + bucket.txBytes
        }
        stats.close()
        return result
    }

    private fun labelForUid(pm: android.content.pm.PackageManager, uid: Int): String? {
        val packages = pm.getPackagesForUid(uid) ?: return null
        val pkg = packages.firstOrNull() ?: return null
        return runCatching {
            pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString()
        }.getOrNull() ?: pkg
    }
}
