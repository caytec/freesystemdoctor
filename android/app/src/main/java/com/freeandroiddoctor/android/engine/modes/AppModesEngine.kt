package com.freeandroiddoctor.android.engine.modes

import com.freeandroiddoctor.android.data.modes.AppMode
import com.freeandroiddoctor.android.data.modes.BuiltInModes
import com.freeandroiddoctor.android.data.modes.ModeSnapshot
import com.freeandroiddoctor.android.data.modes.ModeStore
import com.freeandroiddoctor.android.data.privacy.BuiltInProfiles
import com.freeandroiddoctor.android.data.privacy.PrivacyProfile
import com.freeandroiddoctor.android.data.privacy.PrivacyProfileStore
import com.freeandroiddoctor.android.data.settings.AppSettings
import com.freeandroiddoctor.android.data.settings.SettingsRepository
import com.freeandroiddoctor.android.work.WorkScheduler
import kotlinx.coroutines.flow.first

/**
 * Activates and deactivates [AppMode]s. Captures the pre-activation state in a
 * [ModeSnapshot] so deactivation restores it exactly. Only one mode can be active
 * at a time — activating mode B while A is active first restores A.
 */
class AppModesEngine(
    private val modeStore: ModeStore,
    private val privacyStore: PrivacyProfileStore,
    private val settings: SettingsRepository,
    private val workScheduler: WorkScheduler,
) {

    suspend fun activate(mode: AppMode) {
        modeStore.activeSnapshotOnce()?.let { prior ->
            if (prior.activeModeId != mode.id) restoreInternal(prior)
        }

        val current: AppSettings = settings.settings.first()
        val snapshot = ModeSnapshot(
            activeModeId = mode.id,
            priorDarkTheme = mode.applyDarkTheme?.let { current.darkTheme },
            priorScheduledClean = if (mode.pauseScheduledClean) current.scheduledCleaning else null,
            activatedAt = System.currentTimeMillis(),
        )

        mode.applyDarkTheme?.let { settings.setDarkTheme(it) }
        if (mode.pauseScheduledClean && current.scheduledCleaning) {
            settings.setScheduledCleaning(false)
            workScheduler.setScheduledCleaning(false)
        }
        mode.privacyProfileId?.let { privacyStore.setActiveProfile(it) }

        modeStore.setActiveSnapshot(snapshot)
    }

    suspend fun deactivate() {
        val snapshot = modeStore.activeSnapshotOnce() ?: return
        restoreInternal(snapshot)
        modeStore.setActiveSnapshot(null)
    }

    suspend fun activeMode(): AppMode? {
        val snapshot = modeStore.activeSnapshotOnce() ?: return null
        return modeStore.allModesOnce().firstOrNull { it.id == snapshot.activeModeId }
    }

    suspend fun reapplyOnBoot() {
        val snapshot = modeStore.activeSnapshotOnce() ?: return
        val mode = modeStore.allModesOnce().firstOrNull { it.id == snapshot.activeModeId } ?: return
        mode.applyDarkTheme?.let { settings.setDarkTheme(it) }
        if (mode.pauseScheduledClean) {
            settings.setScheduledCleaning(false)
            workScheduler.setScheduledCleaning(false)
        }
        mode.privacyProfileId?.let { privacyStore.setActiveProfile(it) }
    }

    suspend fun availableProfilesFor(mode: AppMode): PrivacyProfile? {
        val id = mode.privacyProfileId ?: return null
        return (BuiltInProfiles.all + privacyStore.customProfiles.first()).firstOrNull { it.id == id }
    }

    suspend fun allModes(): List<AppMode> = modeStore.allModesOnce()

    private suspend fun restoreInternal(snapshot: ModeSnapshot) {
        snapshot.priorDarkTheme?.let { settings.setDarkTheme(it) }
        snapshot.priorScheduledClean?.let { wasOn ->
            settings.setScheduledCleaning(wasOn)
            workScheduler.setScheduledCleaning(wasOn)
        }
        privacyStore.setActiveProfile(null)
    }
}

/** Convenience accessor for built-ins (UI imports the data layer once). */
object Modes {
    val builtIn = BuiltInModes.all
}
