package com.freeandroiddoctor.android.ui.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.permission.PermissionState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class OnboardingViewModel : ViewModel() {

    private val permissions = ServiceLocator.permissionManager
    private val settings = ServiceLocator.settingsRepository

    private val _state = MutableStateFlow(permissions.snapshot())
    val state: StateFlow<PermissionState> = _state.asStateFlow()

    fun refresh() {
        _state.value = permissions.snapshot()
    }

    fun finish(onDone: () -> Unit) {
        viewModelScope.launch {
            settings.setOnboardingDone(true)
            onDone()
        }
    }
}
