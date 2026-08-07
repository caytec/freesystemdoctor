package com.freeandroiddoctor.android.engine.privacy

import android.app.KeyguardManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.os.Build
import android.provider.Settings
import androidx.biometric.BiometricManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.concurrent.TimeUnit

/** A single pass/warn/fail check on the device's security hygiene. */
data class PostureCheck(
    val id: Id,
    val status: Status,
    /** Extra number the UI can format into the message (days, count…). */
    val detail: Int = 0,
) {
    enum class Id {
        SECURITY_PATCH,
        OS_VERSION,
        SCREEN_LOCK,
        BIOMETRICS,
        ADB_ENABLED,
        DEVELOPER_OPTIONS,
        UNKNOWN_SOURCES_APPS,
    }

    enum class Status { OK, WARN, FAIL }
}

/** An app holding one of the "super permissions" that grant broad control. */
data class PowerfulApp(
    val packageName: String,
    val label: String,
    val kind: Kind,
) {
    enum class Kind { ACCESSIBILITY, NOTIFICATION_LISTENER, OVERLAY, ALL_FILES_ACCESS }
}

data class PostureReport(
    val checks: List<PostureCheck>,
    val powerfulApps: List<PowerfulApp>,
    val patchDate: String,
    val androidVersion: String,
) {
    val score: Int
        get() {
            if (checks.isEmpty()) return 100
            val penalty = checks.fold(0) { acc, check ->
                acc + when (check.status) {
                    PostureCheck.Status.FAIL -> 20
                    PostureCheck.Status.WARN -> 8
                    PostureCheck.Status.OK -> 0
                }
            }
            return (100 - penalty).coerceIn(0, 100)
        }
}

/**
 * Device security-hygiene checkup, plus an inventory of the apps holding "super
 * permissions" — accessibility services, notification listeners, screen overlays and
 * all-files access. That inventory is the part almost no cleaner ships, and it is exactly
 * where stalkerware hides.
 *
 * Everything is read-only and local. Deliberately NOT included: SELinux enforce state and
 * verified-boot flags (unreliable/blocked on modern Android) and Play Integrity (a network
 * call to Google, which would break the local-only promise). This is a hygiene checkup —
 * it is not, and is never called, an antivirus.
 */
class SecurityPostureEngine(private val context: Context) {

    suspend fun scan(): PostureReport = withContext(Dispatchers.IO) { buildReport() }

    private fun buildReport(): PostureReport {
        val checks = ArrayList<PostureCheck>()

        val patchAgeDays = securityPatchAgeDays()
        checks += PostureCheck(
            id = PostureCheck.Id.SECURITY_PATCH,
            status = when {
                patchAgeDays < 0 -> PostureCheck.Status.WARN
                patchAgeDays <= 90 -> PostureCheck.Status.OK
                patchAgeDays <= 365 -> PostureCheck.Status.WARN
                else -> PostureCheck.Status.FAIL
            },
            detail = patchAgeDays.coerceAtLeast(0),
        )

        checks += PostureCheck(
            id = PostureCheck.Id.OS_VERSION,
            status = when {
                Build.VERSION.SDK_INT >= 33 -> PostureCheck.Status.OK
                Build.VERSION.SDK_INT >= 30 -> PostureCheck.Status.WARN
                else -> PostureCheck.Status.FAIL
            },
            detail = Build.VERSION.SDK_INT,
        )

        val keyguard = context.getSystemService(Context.KEYGUARD_SERVICE) as? KeyguardManager
        val secured = runCatching { keyguard?.isDeviceSecure == true }.getOrDefault(false)
        checks += PostureCheck(
            id = PostureCheck.Id.SCREEN_LOCK,
            status = if (secured) PostureCheck.Status.OK else PostureCheck.Status.FAIL,
        )

        val biometricOk = runCatching {
            BiometricManager.from(context)
                .canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG) ==
                BiometricManager.BIOMETRIC_SUCCESS
        }.getOrDefault(false)
        checks += PostureCheck(
            id = PostureCheck.Id.BIOMETRICS,
            status = if (biometricOk) PostureCheck.Status.OK else PostureCheck.Status.WARN,
        )

        checks += PostureCheck(
            id = PostureCheck.Id.ADB_ENABLED,
            status = if (globalFlag(Settings.Global.ADB_ENABLED)) {
                PostureCheck.Status.WARN
            } else {
                PostureCheck.Status.OK
            },
        )
        checks += PostureCheck(
            id = PostureCheck.Id.DEVELOPER_OPTIONS,
            status = if (globalFlag(Settings.Global.DEVELOPMENT_SETTINGS_ENABLED)) {
                PostureCheck.Status.WARN
            } else {
                PostureCheck.Status.OK
            },
        )

        val sideloaded = sideloadedCount()
        checks += PostureCheck(
            id = PostureCheck.Id.UNKNOWN_SOURCES_APPS,
            status = when {
                sideloaded == 0 -> PostureCheck.Status.OK
                sideloaded <= 5 -> PostureCheck.Status.WARN
                else -> PostureCheck.Status.FAIL
            },
            detail = sideloaded,
        )

        return PostureReport(
            checks = checks,
            powerfulApps = powerfulApps(),
            patchDate = Build.VERSION.SECURITY_PATCH.orEmpty(),
            androidVersion = Build.VERSION.RELEASE.orEmpty(),
        )
    }

    private fun globalFlag(key: String): Boolean = runCatching {
        Settings.Global.getInt(context.contentResolver, key, 0) == 1
    }.getOrDefault(false)

    private fun securityPatchAgeDays(): Int {
        val raw = Build.VERSION.SECURITY_PATCH
        if (raw.isNullOrBlank()) return -1
        return runCatching {
            val parsed = SimpleDateFormat("yyyy-MM-dd", Locale.US).parse(raw) ?: return -1
            TimeUnit.MILLISECONDS.toDays(System.currentTimeMillis() - parsed.time).toInt()
        }.getOrDefault(-1)
    }

    /** Apps installed from somewhere other than an app store. */
    private fun sideloadedCount(): Int = runCatching {
        val pm = context.packageManager
        pm.getInstalledApplications(0)
            .filter { (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 }
            .filter { it.packageName != context.packageName }
            .count { app ->
                val installer = runCatching {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                        pm.getInstallSourceInfo(app.packageName).installingPackageName
                    } else {
                        @Suppress("DEPRECATION")
                        pm.getInstallerPackageName(app.packageName)
                    }
                }.getOrNull()
                installer == null || installer !in KNOWN_STORES
            }
    }.getOrDefault(0)

    private fun powerfulApps(): List<PowerfulApp> {
        val pm = context.packageManager
        val out = ArrayList<PowerfulApp>()

        fun label(pkg: String): String = runCatching {
            pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString()
        }.getOrDefault(pkg)

        // Accessibility services and notification listeners are stored as
        // colon-separated component lists in Settings.Secure.
        secureList(Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES).forEach { pkg ->
            out += PowerfulApp(pkg, label(pkg), PowerfulApp.Kind.ACCESSIBILITY)
        }
        secureList(NOTIFICATION_LISTENERS_KEY).forEach { pkg ->
            out += PowerfulApp(pkg, label(pkg), PowerfulApp.Kind.NOTIFICATION_LISTENER)
        }

        runCatching {
            pm.getInstalledApplications(0)
                .filter { (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 }
                .forEach { app ->
                    val requested = runCatching {
                        pm.getPackageInfo(app.packageName, android.content.pm.PackageManager.GET_PERMISSIONS)
                            .requestedPermissions?.toList().orEmpty()
                    }.getOrDefault(emptyList())
                    if (android.Manifest.permission.SYSTEM_ALERT_WINDOW in requested) {
                        out += PowerfulApp(
                            app.packageName, label(app.packageName), PowerfulApp.Kind.OVERLAY,
                        )
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R &&
                        MANAGE_EXTERNAL_STORAGE in requested
                    ) {
                        out += PowerfulApp(
                            app.packageName, label(app.packageName), PowerfulApp.Kind.ALL_FILES_ACCESS,
                        )
                    }
                }
        }

        return out.distinctBy { it.packageName to it.kind }
            .sortedWith(compareBy({ it.kind.ordinal }, { it.label.lowercase() }))
    }

    private fun secureList(key: String): List<String> = runCatching {
        Settings.Secure.getString(context.contentResolver, key)
            ?.split(':')
            ?.filter { it.isNotBlank() }
            ?.mapNotNull { it.substringBefore('/').takeIf { p -> p.isNotBlank() } }
            ?.distinct()
            .orEmpty()
    }.getOrDefault(emptyList())

    private companion object {
        const val NOTIFICATION_LISTENERS_KEY = "enabled_notification_listeners"
        const val MANAGE_EXTERNAL_STORAGE = "android.permission.MANAGE_EXTERNAL_STORAGE"
        val KNOWN_STORES = setOf(
            "com.android.vending",
            "com.google.android.packageinstaller",
            "com.android.packageinstaller",
            "com.amazon.venezia",
            "com.sec.android.app.samsungapps",
            "org.fdroid.fdroid",
            "com.huawei.appmarket",
            "com.xiaomi.market",
            "com.oppo.market",
            "com.heytap.market",
        )
    }
}
