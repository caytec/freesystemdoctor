package com.freesystemdoctor.android.ui.tools

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ToolsViewModel : ViewModel() {

    private val settings = ServiceLocator.settingsRepository

    private val _advancedMode = MutableStateFlow(false)
    val advancedMode: StateFlow<Boolean> = _advancedMode.asStateFlow()

    init {
        viewModelScope.launch {
            settings.settings.collect { _advancedMode.value = it.advancedMode }
        }
    }
}
