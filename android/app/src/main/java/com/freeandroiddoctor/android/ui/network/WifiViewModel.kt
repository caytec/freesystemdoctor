package com.freeandroiddoctor.android.ui.network

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.network.WifiNetwork
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class WifiUiState(
    val hasLocation: Boolean = false,
    val scanning: Boolean = false,
    val networks: List<WifiNetwork> = emptyList(),
)

class WifiViewModel : ViewModel() {

    private val engine = ServiceLocator.wifiAnalyzerEngine

    private val _state = MutableStateFlow(WifiUiState())
    val state: StateFlow<WifiUiState> = _state.asStateFlow()

    fun refreshPermission() {
        _state.update { it.copy(hasLocation = engine.hasLocationPermission()) }
        if (engine.hasLocationPermission()) scan()
    }

    fun scan() {
        _state.update { it.copy(scanning = true) }
        viewModelScope.launch {
            val networks = engine.scan()
            _state.update { it.copy(scanning = false, networks = networks, hasLocation = true) }
        }
    }
}
