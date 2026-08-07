package com.freeandroiddoctor.android.engine.trust

import com.freeandroiddoctor.android.engine.apps.PermissionAuditEngine
import com.freeandroiddoctor.android.engine.network.DataUsageEngine
import com.freeandroiddoctor.android.engine.privacy.ApkStaticScannerEngine
import com.freeandroiddoctor.android.engine.privacy.TrackerScannerEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** One reason the score was reduced, shown verbatim to the user. */
data class TrustDeduction(val kind: Kind, val points: Int, val detail: Int) {
    enum class Kind { TRACKERS, DANGEROUS_PERMISSIONS, RISK_SIGNALS, BACKGROUND_TRAFFIC }
}

data class AppTrust(
    val packageName: String,
    val label: String,
    val score: Int,
    val deductions: List<TrustDeduction>,
    val trackerCount: Int,
    val dangerousPermCount: Int,
    val backgroundBytes: Long,
) {
    val grade: Grade get() = Grade.of(score)

    enum class Grade { A, B, C, D, F;
        companion object {
            fun of(score: Int) = when {
                score >= 85 -> A
                score >= 70 -> B
                score >= 50 -> C
                score >= 30 -> D
                else -> F
            }
        }
    }
}

data class TrustReport(val apps: List<AppTrust>) {
    val averageScore: Int get() =
        if (apps.isEmpty()) 100 else apps.sumOf { it.score } / apps.size
    val leastTrusted: List<AppTrust> get() = apps.sortedBy { it.score }
}

/** Coarse progress so the UI can show which pass is running. */
data class TrustProgress(val phase: Phase) {
    enum class Phase { TRACKERS, PERMISSIONS, RISK, NETWORK, COMBINING }
}

/**
 * Composite per-app trust score — the one number that explains itself.
 *
 * Every competitor shows at most a single dimension (an antivirus verdict, a permission
 * list, a data-usage chart). We already compute four independent local signals, so we can
 * combine them and, crucially, show the user exactly why an app scored what it scored:
 *
 *  - embedded tracking SDKs           ([TrackerScannerEngine])
 *  - granted dangerous permissions    ([PermissionAuditEngine])
 *  - static risk signals              ([ApkStaticScannerEngine])
 *  - background network traffic       ([DataUsageEngine])
 *
 * Scores start at 100 and only ever go down, each deduction is capped so no single signal
 * can dominate, and every deduction is returned so the UI can justify it. Nothing here
 * leaves the device and no verdict is fetched from a server.
 */
class AppTrustEngine(
    private val trackerScanner: TrackerScannerEngine,
    private val permissionAudit: PermissionAuditEngine,
    private val riskScanner: ApkStaticScannerEngine,
    private val dataUsage: DataUsageEngine,
) {

    suspend fun scan(onProgress: (TrustProgress) -> Unit = {}): TrustReport =
        withContext(Dispatchers.IO) {
            onProgress(TrustProgress(TrustProgress.Phase.TRACKERS))
            val trackers = runCatching { trackerScanner.scan() }.getOrNull()
                ?.apps?.associateBy { it.packageName } ?: emptyMap()

            onProgress(TrustProgress(TrustProgress.Phase.PERMISSIONS))
            val permissions = runCatching { permissionAudit.audit() }.getOrDefault(emptyList())

            onProgress(TrustProgress(TrustProgress.Phase.RISK))
            val risk = runCatching { riskScanner.scan() }.getOrNull()
                ?.apps?.associateBy { it.packageName } ?: emptyMap()

            onProgress(TrustProgress(TrustProgress.Phase.NETWORK))
            val background = runCatching { dataUsage.backgroundActivity() }
                .getOrDefault(emptyList())
                .associate { it.packageName to it.backgroundBytes }

            onProgress(TrustProgress(TrustProgress.Phase.COMBINING))
            // The permission audit is the canonical list of user-installed apps.
            val apps = permissions.map { audited ->
                score(
                    packageName = audited.packageName,
                    label = audited.label,
                    trackerCount = trackers[audited.packageName]?.count ?: 0,
                    dangerousPermCount = audited.grantedDangerous.size,
                    riskScore = risk[audited.packageName]?.riskScore ?: 0,
                    backgroundBytes = background[audited.packageName] ?: 0L,
                )
            }.sortedBy { it.score }

            TrustReport(apps)
        }

    private fun score(
        packageName: String,
        label: String,
        trackerCount: Int,
        dangerousPermCount: Int,
        riskScore: Int,
        backgroundBytes: Long,
    ): AppTrust {
        val deductions = ArrayList<TrustDeduction>()

        if (trackerCount > 0) {
            val points = (trackerCount * POINTS_PER_TRACKER).coerceAtMost(MAX_TRACKER_PENALTY)
            deductions += TrustDeduction(
                TrustDeduction.Kind.TRACKERS, points, trackerCount,
            )
        }
        if (dangerousPermCount > 0) {
            val points = (dangerousPermCount * POINTS_PER_PERMISSION)
                .coerceAtMost(MAX_PERMISSION_PENALTY)
            deductions += TrustDeduction(
                TrustDeduction.Kind.DANGEROUS_PERMISSIONS, points, dangerousPermCount,
            )
        }
        if (riskScore > 0) {
            val points = (riskScore / RISK_DIVISOR).coerceAtMost(MAX_RISK_PENALTY)
            if (points > 0) {
                deductions += TrustDeduction(
                    TrustDeduction.Kind.RISK_SIGNALS, points, riskScore,
                )
            }
        }
        if (backgroundBytes > 0) {
            val megabytes = (backgroundBytes / (1024 * 1024)).toInt()
            val points = (megabytes / MB_PER_POINT).coerceAtMost(MAX_TRAFFIC_PENALTY)
            if (points > 0) {
                deductions += TrustDeduction(
                    TrustDeduction.Kind.BACKGROUND_TRAFFIC, points, megabytes,
                )
            }
        }

        val score = (100 - deductions.sumOf { it.points }).coerceIn(0, 100)
        return AppTrust(
            packageName = packageName,
            label = label,
            score = score,
            deductions = deductions.sortedByDescending { it.points },
            trackerCount = trackerCount,
            dangerousPermCount = dangerousPermCount,
            backgroundBytes = backgroundBytes,
        )
    }

    private companion object {
        // Each signal is capped so one dimension can't sink an app on its own.
        const val POINTS_PER_TRACKER = 4
        const val MAX_TRACKER_PENALTY = 32
        const val POINTS_PER_PERMISSION = 3
        const val MAX_PERMISSION_PENALTY = 24
        const val RISK_DIVISOR = 4
        const val MAX_RISK_PENALTY = 25
        const val MB_PER_POINT = 50
        const val MAX_TRAFFIC_PENALTY = 15
    }
}
