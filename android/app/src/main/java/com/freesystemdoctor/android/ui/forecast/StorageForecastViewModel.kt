package com.freesystemdoctor.android.ui.forecast

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.forecast.ForecastResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ForecastUiState(
    val result: ForecastResult? = null,
    val loading: Boolean = true,
)

class StorageForecastViewModel : ViewModel() {

    private val engine = ServiceLocator.storageForecastEngine
    private val scheduler = ServiceLocator.workScheduler

    private val _state = MutableStateFlow(ForecastUiState())
    val state: StateFlow<ForecastUiState> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            engine.recordToday()
            val result = engine.forecast()
            _state.value = ForecastUiState(result = result, loading = false)
            scheduler.setStorageSnapshots(true)
        }
    }
}
