package com.freesystemdoctor.android.ui.memory

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.memory.MemoryInfo
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MemoryUiState(
    val info: MemoryInfo? = null,
    val working: Boolean = false,
    val lastFreedBytes: Long? = null,
)

class MemoryViewModel : ViewModel() {

    private val engine = ServiceLocator.memoryEngine
    private val _state = MutableStateFlow(MemoryUiState())
    val state: StateFlow<MemoryUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(info = engine.read()) }
    }

    fun freeBackground() {
        if (_state.value.working) return
        _state.update { it.copy(working = true, lastFreedBytes = null) }
        viewModelScope.launch {
            val freed = engine.freeBackground()
            _state.update { it.copy(working = false, lastFreedBytes = freed, info = engine.read()) }
        }
    }
}
