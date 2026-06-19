package com.freeandroiddoctor.android.engine.focus

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.provider.Settings

/**
 * Focus session state + DND control. The actual session lifecycle is owned by
 * [com.freeandroiddoctor.android.service.FocusSessionService]; this engine is just a
 * stateless helper around the system NotificationManager.
 *
 * We deliberately use INTERRUPTION_FILTER_PRIORITY (not _NONE) so emergency alerts and
 * the user's chosen DND priority channels still come through — "honest brand", and
 * matches what most people actually want from a focus mode.
 */
class FocusEngine(private val context: Context) {

    fun hasDndAccess(): Boolean {
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        return nm.isNotificationPolicyAccessGranted
    }

    fun dndSettingsIntent(): Intent =
        Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    /** Returns the previous filter so callers can restore it on session end. */
    fun enterDnd(): Int {
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val previous = nm.currentInterruptionFilter
        if (nm.isNotificationPolicyAccessGranted) {
            nm.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_PRIORITY)
        }
        return previous
    }

    fun restoreDnd(previousFilter: Int) {
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.isNotificationPolicyAccessGranted) {
            nm.setInterruptionFilter(previousFilter)
        }
    }
}
