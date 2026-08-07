package com.freeandroiddoctor.android.engine.privacy

import android.app.usage.StorageStatsManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Process
import android.os.UserHandle
import android.os.storage.StorageManager
import android.provider.Settings
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class BrowserDataEntry(
    val packageName: String,
    val label: String,
    val cacheBytes: Long,
    val dataBytes: Long,
) {
    val totalBytes: Long get() = cacheBytes + dataBytes
}

/**
 * Reports cache + data bytes used by installed browsers. We can't programmatically
 * clear another app's cookies on modern Android — the "clear" action launches the
 * system app-info screen so the user can wipe in one tap.
 */
class BrowserDataEngine(private val context: Context) {

    suspend fun scan(): List<BrowserDataEntry> = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val ssm = context.getSystemService(StorageStatsManager::class.java)
        val sm = context.getSystemService(StorageManager::class.java)
        val uuid = sm?.getUuidForPath(context.filesDir) ?: StorageManager.UUID_DEFAULT
        val user: UserHandle = Process.myUserHandle()

        BROWSER_PACKAGES.mapNotNull { pkg ->
            val info = runCatching { pm.getApplicationInfo(pkg, 0) }.getOrNull() ?: return@mapNotNull null
            val stats = ssm?.let { runCatching { it.queryStatsForPackage(uuid, pkg, user) }.getOrNull() }
            val label = runCatching { pm.getApplicationLabel(info).toString() }.getOrNull() ?: pkg
            BrowserDataEntry(
                packageName = pkg,
                label = label,
                cacheBytes = stats?.cacheBytes ?: 0L,
                dataBytes = stats?.dataBytes ?: 0L,
            )
        }.sortedByDescending { it.totalBytes }
    }

    fun appInfoIntent(packageName: String): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", packageName, null)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }

    private companion object {
        val BROWSER_PACKAGES = listOf(
            "com.android.chrome",
            "com.chrome.beta",
            "com.chrome.dev",
            "org.mozilla.firefox",
            "org.mozilla.fenix",
            "com.microsoft.emmx",
            "com.brave.browser",
            "com.opera.browser",
            "com.opera.mini.native",
            "com.sec.android.app.sbrowser",
            "com.duckduckgo.mobile.android",
            "com.vivaldi.browser",
            "org.torproject.torbrowser",
            "com.kiwibrowser.browser",
            "com.UCMobile.intl",
        )
    }
}
