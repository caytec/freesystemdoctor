package com.freesystemdoctor.android.ui.focus

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.service.FocusSessionService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class FocusUiState(
    val dndGranted: Boolean = false,
    val running: Boolean = false,
)

class FocusViewModel(application: Application) : AndroidViewModel(application) {

    private val engine = ServiceLocator.focusEngine

    private val _state = MutableStateFlow(FocusUiState())
    val state: StateFlow<FocusUiState> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        _state.value = _state.value.copy(dndGranted = engine.hasDndAccess())
    }

    fun start() {
        val ctx = getApplication<Application>()
        FocusSessionService.start(ctx)
        _state.value = _state.value.copy(running = true)
    }

    fun end() {
        val ctx = getApplication<Application>()
        FocusSessionService.stop(ctx)
        _state.value = _state.value.copy(running = false)
    }

    fun dndIntent() = engine.dndSettingsIntent()
}
