package com.freeandroiddoctor.android.ui.memory

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.apps.AppListItem
import com.freeandroiddoctor.android.engine.apps.AppSort
import com.freeandroiddoctor.android.engine.memory.MemoryInfo
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MemoryUiState(
    val info: MemoryInfo? = null,
    val working: Boolean = false,
    val lastFreedBytes: Long? = null,
    /** Set when the platform (Android 14+) refuses to reclaim other apps at all. */
    val reclaimUnsupported: Boolean = false,
    val largeApps: List<AppListItem> = emptyList(),
    val loadingApps: Boolean = false,
)

class MemoryViewModel : ViewModel() {

    private val engine = ServiceLocator.memoryEngine
    private val appManager = ServiceLocator.appManagerEngine
    private val _state = MutableStateFlow(MemoryUiState())
    val state: StateFlow<MemoryUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(info = engine.read(), loadingApps = true) }
        viewModelScope.launch {
            val apps = runCatching {
                appManager.listApps(includeSystem = false, sort = AppSort.SIZE)
            }.getOrDefault(emptyList())
            _state.update { it.copy(largeApps = apps.take(MAX_APPS), loadingApps = false) }
        }
    }

    /** True when the platform still permits reclaiming other apps' background processes. */
    val reclaimSupported: Boolean get() = engine.canReclaimOtherApps

    fun freeBackground() {
        if (_state.value.working) return
        _state.update { it.copy(working = true, lastFreedBytes = null, reclaimUnsupported = false) }
        viewModelScope.launch {
            val result = engine.freeBackground()
            _state.update {
                it.copy(
                    working = false,
                    // Only surface a byte figure when the platform actually did something.
                    lastFreedBytes = if (result.supported) result.freedBytes else null,
                    reclaimUnsupported = !result.supported,
                    info = engine.read(),
                )
            }
        }
    }

    /** Refresh after the user returns from the system uninstall flow. */
    fun refreshApps() {
        viewModelScope.launch {
            val apps = runCatching {
                appManager.listApps(includeSystem = false, sort = AppSort.SIZE)
            }.getOrDefault(emptyList())
            _state.update { it.copy(largeApps = apps.take(MAX_APPS), info = engine.read()) }
        }
    }

    private companion object {
        const val MAX_APPS = 25
    }
}
