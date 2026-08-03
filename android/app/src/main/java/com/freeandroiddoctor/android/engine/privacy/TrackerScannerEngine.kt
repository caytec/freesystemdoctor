package com.freeandroiddoctor.android.engine.privacy

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlin.coroutines.coroutineContext

/** Trackers found inside one app. */
data class AppTrackers(
    val packageName: String,
    val label: String,
    val trackers: List<TrackerSignature>,
) {
    val count: Int get() = trackers.size
}

data class TrackerScanProgress(val done: Int, val total: Int)

data class TrackerReport(
    val apps: List<AppTrackers>,
    val scannedApps: Int,
) {
    /** Apps carrying at least one detected tracker. */
    val appsWithTrackers: Int get() = apps.size

    /** Ranking of the most widespread trackers across the device. */
    val topTrackers: List<Pair<TrackerSignature, Int>>
        get() = apps.flatMap { it.trackers }
            .groupingBy { it }
            .eachCount()
            .entries
            .sortedByDescending { it.value }
            .map { it.key to it.value }
}

/**
 * Detects third-party tracking / ad SDKs embedded in installed apps by matching the
 * components each app declares against the offline [TrackerDb] signature list.
 *
 * Everything is local: the signature DB ships with the app and no package list, app name
 * or scan result ever leaves the device — unlike web-based tracker lookups.
 *
 * Implementation note: component flags are requested **per package**, never in one bulk
 * `getInstalledPackages` call — asking for activities+services+receivers+providers for
 * every app at once reliably overflows the 1 MB Binder transaction buffer on devices with
 * many apps.
 */
class TrackerScannerEngine(private val context: Context) {

    suspend fun scan(
        includeSystem: Boolean = false,
        onProgress: (TrackerScanProgress) -> Unit = {},
    ): TrackerReport = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val packages = runCatching { pm.getInstalledApplications(0) }
            .getOrDefault(emptyList())
            .filter { includeSystem || (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 }
            .filter { it.packageName != context.packageName }

        val results = ArrayList<AppTrackers>()
        packages.forEachIndexed { index, appInfo ->
            coroutineContext.ensureActive()
            onProgress(TrackerScanProgress(index + 1, packages.size))

            val info = runCatching {
                pm.getPackageInfo(appInfo.packageName, COMPONENT_FLAGS)
            }.getOrNull() ?: return@forEachIndexed

            val found = detect(info)
            if (found.isNotEmpty()) {
                results += AppTrackers(
                    packageName = appInfo.packageName,
                    label = runCatching { pm.getApplicationLabel(appInfo).toString() }
                        .getOrDefault(appInfo.packageName),
                    trackers = found,
                )
            }
        }

        TrackerReport(
            apps = results.sortedByDescending { it.count },
            scannedApps = packages.size,
        )
    }

    private fun detect(info: PackageInfo): List<TrackerSignature> {
        val classNames = sequence {
            info.activities?.forEach { yield(it.name) }
            info.services?.forEach { yield(it.name) }
            info.receivers?.forEach { yield(it.name) }
            info.providers?.forEach { yield(it.name) }
        }
        val found = LinkedHashSet<TrackerSignature>()
        for (name in classNames) {
            if (name == null) continue
            for ((prefix, signature) in TrackerDb.byPrefix) {
                if (name.startsWith(prefix)) found += signature
            }
        }
        return found.toList().sortedBy { it.name }
    }

    private companion object {
        const val COMPONENT_FLAGS = PackageManager.GET_ACTIVITIES or
            PackageManager.GET_SERVICES or
            PackageManager.GET_RECEIVERS or
            PackageManager.GET_PROVIDERS
    }
}
