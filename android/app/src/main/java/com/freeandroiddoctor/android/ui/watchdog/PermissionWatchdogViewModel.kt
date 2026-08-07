package com.freeandroiddoctor.android.ui.watchdog

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.watchdog.PermChange
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class WatchdogUiState(
    val scanning: Boolean = false,
    val scanned: Boolean = false,
    val firstRun: Boolean = false,
    val changes: List<PermChange> = emptyList(),
    val scannedApps: Int = 0,
)

class PermissionWatchdogViewModel : ViewModel() {

    private val engine = ServiceLocator.permissionWatchdogEngine

    private val _state = MutableStateFlow(WatchdogUiState())
    val state: StateFlow<WatchdogUiState> = _state.asStateFlow()

    fun scan() {
        if (_state.value.scanning) return
        _state.value = WatchdogUiState(scanning = true)
        viewModelScope.launch {
            runCatching { engine.scan(persist = true) }
                .onSuccess { r ->
                    _state.value = WatchdogUiState(
                        scanning = false,
                        scanned = true,
                        firstRun = r.firstRun,
                        changes = r.changes,
                        scannedApps = r.scannedApps,
                    )
                }
                .onFailure { _state.value = WatchdogUiState(scanning = false, scanned = true) }
        }
    }
}
