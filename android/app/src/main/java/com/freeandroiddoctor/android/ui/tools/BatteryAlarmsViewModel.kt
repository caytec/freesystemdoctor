package com.freeandroiddoctor.android.ui.tools

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class BatteryAlarmsUiState(
    val enabled: Boolean = false,
    val low: Int = 15,
    val full: Int = 80,
)

class BatteryAlarmsViewModel : ViewModel() {

    private val settings = ServiceLocator.settingsRepository
    private val scheduler = ServiceLocator.workScheduler

    private val _state = MutableStateFlow(BatteryAlarmsUiState())
    val state: StateFlow<BatteryAlarmsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            settings.settings.collect {
                _state.value = BatteryAlarmsUiState(
                    enabled = it.batteryAlarmsEnabled,
                    low = it.batteryAlarmLow,
                    full = it.batteryAlarmFull,
                )
            }
        }
    }

    fun setEnabled(value: Boolean) {
        viewModelScope.launch {
            settings.setBatteryAlarms(value)
            scheduler.setBatteryAlarms(value)
        }
    }

    fun setThresholds(low: Int, full: Int) {
        viewModelScope.launch { settings.setBatteryAlarmThresholds(low, full) }
    }
}
