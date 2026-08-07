package com.freeandroiddoctor.android.ui.performance

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.performance.PerformanceReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PerformanceUiState(
    val loading: Boolean = true,
    val report: PerformanceReport? = null,
    val reclaiming: Boolean = false,
    /** Bytes actually freed by the last cache reclaim; null until one runs. */
    val lastReclaimedBytes: Long? = null,
)

class PerformanceViewModel : ViewModel() {

    private val engine = ServiceLocator.performanceEngine

    private val _state = MutableStateFlow(PerformanceUiState())
    val state: StateFlow<PerformanceUiState> = _state.asStateFlow()

    fun load() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            runCatching { engine.analyze() }
                .onSuccess { _state.value = PerformanceUiState(loading = false, report = it) }
                .onFailure { _state.value = _state.value.copy(loading = false) }
        }
    }

    /** Frees other apps' caches through the platform. Storage only — never sold as speed. */
    fun reclaimCache() {
        if (_state.value.reclaiming) return
        _state.value = _state.value.copy(reclaiming = true, lastReclaimedBytes = null)
        viewModelScope.launch {
            val freed = runCatching { engine.reclaimCache() }.getOrDefault(0L)
            val refreshed = runCatching { engine.analyze() }.getOrNull()
            _state.value = _state.value.copy(
                reclaiming = false,
                lastReclaimedBytes = freed,
                report = refreshed ?: _state.value.report,
            )
        }
    }
}
