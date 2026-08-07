package com.freeandroiddoctor.android.ui.network

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.network.SpeedResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SpeedTestUiState(
    val testing: Boolean = false,
    val result: SpeedResult? = null,
)

class SpeedTestViewModel : ViewModel() {

    private val engine = ServiceLocator.speedTestEngine
    private val _state = MutableStateFlow(SpeedTestUiState())
    val state: StateFlow<SpeedTestUiState> = _state.asStateFlow()

    fun run() {
        if (_state.value.testing) return
        _state.update { it.copy(testing = true, result = null) }
        viewModelScope.launch {
            val result = engine.run()
            _state.update { it.copy(testing = false, result = result) }
        }
    }
}
