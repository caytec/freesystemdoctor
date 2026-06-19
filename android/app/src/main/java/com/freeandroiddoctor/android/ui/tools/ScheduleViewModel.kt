package com.freeandroiddoctor.android.ui.tools

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ScheduleViewModel : ViewModel() {

    private val settings = ServiceLocator.settingsRepository
    private val scheduler = ServiceLocator.workScheduler

    private val _enabled = MutableStateFlow(false)
    val enabled: StateFlow<Boolean> = _enabled.asStateFlow()

    init {
        viewModelScope.launch {
            settings.settings.collect { _enabled.value = it.scheduledCleaning }
        }
    }

    fun setEnabled(value: Boolean) {
        viewModelScope.launch {
            settings.setScheduledCleaning(value)
            scheduler.setScheduledCleaning(value)
        }
    }
}
