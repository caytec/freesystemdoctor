package com.freesystemdoctor.android.ui.privacy

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.data.privacy.BuiltInProfiles
import com.freesystemdoctor.android.data.privacy.PrivacyProfile
import com.freesystemdoctor.android.engine.privacy.ProfilePlan
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.launch

data class PrivacyProfilesState(
    val builtIn: List<PrivacyProfile> = BuiltInProfiles.all,
    val custom: List<PrivacyProfile> = emptyList(),
    val activeId: String? = null,
    val plan: ProfilePlan? = null,
    val planning: Boolean = false,
)

class PrivacyProfilesViewModel(app: Application) : AndroidViewModel(app) {

    private val store = ServiceLocator.privacyProfileStore
    private val engine = ServiceLocator.privacyProfileEngine

    private val _plan = MutableStateFlow<ProfilePlan?>(null)
    private val _planning = MutableStateFlow(false)

    val state: StateFlow<PrivacyProfilesState> = combine(
        store.customProfiles, store.activeProfileId, _plan, _planning,
    ) { custom, activeId, plan, planning ->
        PrivacyProfilesState(
            custom = custom,
            activeId = activeId,
            plan = plan,
            planning = planning,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), PrivacyProfilesState())

    fun buildPlan(profile: PrivacyProfile) {
        if (_planning.value) return
        _planning.value = true
        viewModelScope.launch {
            val plan = engine.buildPlan(profile)
            _plan.value = plan
            _planning.value = false
        }
    }

    fun clearPlan() {
        _plan.value = null
    }

    fun finalizePlan() {
        val plan = _plan.value ?: return
        engine.finalize(plan.profile)
        viewModelScope.launch { store.setActiveProfile(plan.profile.id) }
        _plan.value = null
    }
}
