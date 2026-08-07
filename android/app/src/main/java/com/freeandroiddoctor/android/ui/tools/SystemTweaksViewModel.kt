package com.freeandroiddoctor.android.ui.tools

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class SystemTweaksViewModel : ViewModel() {

    private val settings = ServiceLocator.settingsRepository
    private val tweaks = ServiceLocator.systemTweaksEngine

    private val _monitorEnabled = MutableStateFlow(false)
    val monitorEnabled: StateFlow<Boolean> = _monitorEnabled.asStateFlow()

    init {
        viewModelScope.launch {
            settings.settings.collect { _monitorEnabled.value = it.monitorEnabled }
        }
    }

    fun setMonitorPref(enabled: Boolean) {
        viewModelScope.launch { settings.setMonitorEnabled(enabled) }
    }

    fun isIgnoringBatteryOptimizations() = tweaks.isIgnoringBatteryOptimizations()
    fun ignoreBatteryIntent() = tweaks.ignoreBatteryOptimizationsIntent()
    fun dataUsageIntent() = tweaks.dataUsageSettingsIntent()
    fun autostartIntent() = tweaks.autostartIntent()
}
