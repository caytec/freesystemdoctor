package com.freesystemdoctor.android.engine.privacy

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import com.freesystemdoctor.android.data.privacy.PrivacyProfile
import com.freesystemdoctor.android.engine.apps.AuditedApp
import com.freesystemdoctor.android.engine.apps.PermissionAuditEngine
import com.freesystemdoctor.android.engine.system.ClipboardCleanerEngine

/** Step the user is being walked through when applying a profile. */
data class ProfileStep(
    val packageName: String,
    val appLabel: String,
    val violations: List<String>,
    val intent: Intent,
)

data class ProfilePlan(
    val profile: PrivacyProfile,
    val steps: List<ProfileStep>,
    val clipboardWillBeCleared: Boolean,
    val suggestPrivateDns: Boolean,
)

/**
 * Builds an ordered list of "open app settings" intents that walk the user through
 * every app whose granted permissions violate the chosen profile. Android does not
 * let us batch-revoke without root, so the user clicks through; the engine just keeps
 * the order deterministic and skips apps that already comply.
 */
class PrivacyProfileEngine(
    private val context: Context,
    private val audit: PermissionAuditEngine,
    private val clipboard: ClipboardCleanerEngine,
) {

    suspend fun buildPlan(profile: PrivacyProfile, includeSystem: Boolean = false): ProfilePlan {
        val audited = audit.audit(includeSystem = includeSystem)
        val steps = audited.mapNotNull { app -> stepFor(profile, app) }
        return ProfilePlan(
            profile = profile,
            steps = steps,
            clipboardWillBeCleared = profile.clearClipboard,
            suggestPrivateDns = profile.suggestPrivateDns,
        )
    }

    fun finalize(profile: PrivacyProfile) {
        if (profile.clearClipboard) {
            runCatching { clipboard.clear() }
        }
    }

    fun privateDnsSettingsIntent(): Intent =
        Intent(Settings.ACTION_WIRELESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    private fun stepFor(profile: PrivacyProfile, app: AuditedApp): ProfileStep? {
        val grantedFull = app.grantedDangerous.map { "android.permission.$it" }
        val violations = grantedFull.filter { profile.forbidsPermission(it) }
        if (violations.isEmpty()) return null

        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", app.packageName, null)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return ProfileStep(
            packageName = app.packageName,
            appLabel = app.label,
            violations = violations.map { it.substringAfterLast('.') },
            intent = intent,
        )
    }
}
