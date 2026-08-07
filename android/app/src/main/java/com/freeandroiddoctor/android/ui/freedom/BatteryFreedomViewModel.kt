package com.freeandroiddoctor.android.ui.freedom

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.battery.BatteryFreedomReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class FreedomUiState(
    val loading: Boolean = true,
    val report: BatteryFreedomReport? = null,
)

class BatteryFreedomViewModel : ViewModel() {

    private val engine = ServiceLocator.batteryFreedomEngine

    private val _state = MutableStateFlow(FreedomUiState())
    val state: StateFlow<FreedomUiState> = _state.asStateFlow()

    fun load() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            runCatching { engine.scan() }
                .onSuccess { _state.value = FreedomUiState(false, it) }
                .onFailure { _state.value = _state.value.copy(loading = false) }
        }
    }

    /** System screen where a battery-optimization exemption can actually be revoked. */
    fun appDetailsIntent(pkg: String): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:$pkg")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }

    fun batteryOptimizationIntent(): Intent =
        Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}
