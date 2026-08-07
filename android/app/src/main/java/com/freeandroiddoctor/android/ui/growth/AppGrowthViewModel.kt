package com.freeandroiddoctor.android.ui.growth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.forecast.GrowthReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AppGrowthUiState(
    val loading: Boolean = true,
    val report: GrowthReport? = null,
)

class AppGrowthViewModel : ViewModel() {

    private val engine = ServiceLocator.appGrowthEngine

    private val _state = MutableStateFlow(AppGrowthUiState())
    val state: StateFlow<AppGrowthUiState> = _state.asStateFlow()

    fun load() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            runCatching { engine.growth() }
                .onSuccess { _state.value = AppGrowthUiState(false, it) }
                .onFailure { _state.value = _state.value.copy(loading = false) }
        }
    }

    /** Takes a snapshot now so the user doesn't have to wait for the daily worker. */
    fun snapshotNow() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            runCatching {
                engine.recordToday()
                engine.growth()
            }
                .onSuccess { _state.value = AppGrowthUiState(false, it) }
                .onFailure { _state.value = _state.value.copy(loading = false) }
        }
    }
}
