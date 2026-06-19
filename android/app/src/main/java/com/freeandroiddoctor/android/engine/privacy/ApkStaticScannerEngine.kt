package com.freeandroiddoctor.android.engine.privacy

import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build
import android.view.accessibility.AccessibilityManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Per-app static-analysis risk signal, surfaced in [ApkRiskReport.signals]. */
enum class RiskSignal {
    ACCESSIBILITY_SERVICE,
    DEVICE_ADMIN,
    DANGEROUS_PERM_HEAVY,
    UNKNOWN_INSTALLER,
    OUTDATED_TARGET_SDK,
    DEBUG_SIGNED,
    SUSPICIOUS_PACKAGE,
}

data class ApkRiskReport(
    val packageName: String,
    val label: String,
    val isSystem: Boolean,
    val signals: List<RiskSignal>,
    val riskScore: Int,
)

data class DeviceRiskReport(
    val apps: List<ApkRiskReport>,
    val privacyScore: Int,
    val scannedAt: Long = System.currentTimeMillis(),
)

/**
 * Walks installed packages and derives a 0–100 risk score from purely-local signals —
 * no network calls, no opaque blocklist downloads, no `pm grant`/Shizuku usage. The
 * device's overall privacy score is the inverted average of the top-N risky apps.
 */
class ApkStaticScannerEngine(private val context: Context) {

    suspend fun scan(includeSystem: Boolean = false): DeviceRiskReport =
        withContext(Dispatchers.IO) {
            val pm = context.packageManager
            val accessibilityEnabled = runCatching {
                val am = context.getSystemService(AccessibilityManager::class.java)
                am.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
                    .mapNotNull { it.resolveInfo?.serviceInfo?.packageName }
                    .toSet()
            }.getOrDefault(emptySet())

            val infos = pm.getInstalledPackages(
                PackageManager.GET_PERMISSIONS or PackageManager.GET_RECEIVERS,
            )
            val apps = infos.mapNotNull { info ->
                val appInfo = info.applicationInfo ?: return@mapNotNull null
                val isSystem = (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0
                if (!includeSystem && isSystem) return@mapNotNull null
                report(pm, info, appInfo, isSystem, accessibilityEnabled)
            }.sortedByDescending { it.riskScore }

            val topRisks = apps.take(10)
            val privacyScore = if (topRisks.isEmpty()) {
                100
            } else {
                val avg = topRisks.sumOf { it.riskScore } / topRisks.size
                (100 - avg).coerceIn(0, 100)
            }
            DeviceRiskReport(apps = apps, privacyScore = privacyScore)
        }

    private fun report(
        pm: PackageManager,
        info: PackageInfo,
        appInfo: ApplicationInfo,
        isSystem: Boolean,
        accessibilityEnabled: Set<String>,
    ): ApkRiskReport {
        val signals = ArrayList<RiskSignal>()

        if (info.packageName in accessibilityEnabled) signals += RiskSignal.ACCESSIBILITY_SERVICE

        val dangerousGranted = grantedDangerous(info)
        if (dangerousGranted.size >= 4) signals += RiskSignal.DANGEROUS_PERM_HEAVY

        val installer = runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                pm.getInstallSourceInfo(info.packageName).installingPackageName
            } else {
                @Suppress("DEPRECATION")
                pm.getInstallerPackageName(info.packageName)
            }
        }.getOrNull()
        if (!isSystem && installer != null && installer !in TRUSTED_INSTALLERS) {
            signals += RiskSignal.UNKNOWN_INSTALLER
        }

        val currentSdk = Build.VERSION.SDK_INT
        if (appInfo.targetSdkVersion < currentSdk - 4) signals += RiskSignal.OUTDATED_TARGET_SDK

        if ((appInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0) signals += RiskSignal.DEBUG_SIGNED

        val devAdminReceivers = info.receivers?.any {
            it.permission == "android.permission.BIND_DEVICE_ADMIN"
        } ?: false
        if (devAdminReceivers) signals += RiskSignal.DEVICE_ADMIN

        if (SUSPICIOUS_PREFIXES.any { info.packageName.startsWith(it) }) {
            signals += RiskSignal.SUSPICIOUS_PACKAGE
        }

        val weightSum = signals.sumOf { it.weight() }
        val riskScore = weightSum.coerceIn(0, 100)
        val label = runCatching { pm.getApplicationLabel(appInfo).toString() }
            .getOrNull() ?: info.packageName

        return ApkRiskReport(
            packageName = info.packageName,
            label = label,
            isSystem = isSystem,
            signals = signals,
            riskScore = riskScore,
        )
    }

    private fun grantedDangerous(info: PackageInfo): List<String> {
        val names = info.requestedPermissions ?: return emptyList()
        val flags = info.requestedPermissionsFlags ?: return emptyList()
        val out = ArrayList<String>()
        names.forEachIndexed { i, perm ->
            val granted = i < flags.size &&
                (flags[i] and PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0
            if (granted && perm in DANGEROUS) out += perm
        }
        return out
    }

    private fun RiskSignal.weight(): Int = when (this) {
        RiskSignal.ACCESSIBILITY_SERVICE -> 40
        RiskSignal.DEVICE_ADMIN -> 35
        RiskSignal.SUSPICIOUS_PACKAGE -> 35
        RiskSignal.DANGEROUS_PERM_HEAVY -> 25
        RiskSignal.UNKNOWN_INSTALLER -> 15
        RiskSignal.OUTDATED_TARGET_SDK -> 10
        RiskSignal.DEBUG_SIGNED -> 20
    }

    private companion object {
        val TRUSTED_INSTALLERS = setOf(
            "com.android.vending",
            "com.google.android.feedback",
            "com.aurora.store",
            "com.huawei.appmarket",
            "org.fdroid.fdroid",
            "com.amazon.venezia",
            "com.sec.android.app.samsungapps",
        )

        val SUSPICIOUS_PREFIXES = listOf(
            "com.adups.",
            "com.ttt.cdtnet",
            "net.sourceforge.iongram",
        )

        val DANGEROUS = setOf(
            "android.permission.CAMERA",
            "android.permission.RECORD_AUDIO",
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION",
            "android.permission.ACCESS_BACKGROUND_LOCATION",
            "android.permission.READ_CONTACTS",
            "android.permission.READ_SMS",
            "android.permission.SEND_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.READ_CALL_LOG",
            "android.permission.WRITE_CALL_LOG",
            "android.permission.READ_PHONE_STATE",
            "android.permission.READ_CALENDAR",
        )
    }
}
