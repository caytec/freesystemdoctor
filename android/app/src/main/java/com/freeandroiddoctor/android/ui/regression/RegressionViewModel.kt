package com.freeandroiddoctor.android.ui.regression

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.performance.RegressionReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class RegressionUiState(
    val loading: Boolean = true,
    val report: RegressionReport? = null,
)

class RegressionViewModel : ViewModel() {

    private val engine = ServiceLocator.regressionDetectiveEngine

    private val _state = MutableStateFlow(RegressionUiState())
    val state: StateFlow<RegressionUiState> = _state.asStateFlow()

    fun load() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            runCatching { engine.analyze() }
                .onSuccess { _state.value = RegressionUiState(false, it) }
                .onFailure { _state.value = _state.value.copy(loading = false) }
        }
    }

    /** Takes a reading now so the user doesn't have to wait for the daily worker. */
    fun sampleNow() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            runCatching {
                engine.recordToday()
                engine.analyze()
            }
                .onSuccess { _state.value = RegressionUiState(false, it) }
                .onFailure { _state.value = _state.value.copy(loading = false) }
        }
    }
}
