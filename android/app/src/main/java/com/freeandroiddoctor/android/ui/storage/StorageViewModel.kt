package com.freeandroiddoctor.android.ui.storage

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.storage.AppStorage
import com.freeandroiddoctor.android.engine.storage.VolumeInfo
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class StorageUiState(
    val loading: Boolean = false,
    val hasUsageAccess: Boolean = false,
    val volume: VolumeInfo? = null,
    val apps: List<AppStorage> = emptyList(),
)

class StorageViewModel : ViewModel() {

    private val engine = ServiceLocator.storageEngine
    private val permissions = ServiceLocator.permissionManager
    private val _state = MutableStateFlow(StorageUiState())
    val state: StateFlow<StorageUiState> = _state.asStateFlow()

    fun load() {
        val hasAccess = permissions.hasUsageAccess()
        _state.value = _state.value.copy(loading = true, hasUsageAccess = hasAccess)
        viewModelScope.launch {
            // Never leave loading=true (or crash) if the platform call throws.
            runCatching {
                val volume = engine.readPrimaryVolume()
                val apps = if (hasAccess) engine.readPerApp() else emptyList()
                _state.value = StorageUiState(
                    loading = false,
                    hasUsageAccess = hasAccess,
                    volume = volume,
                    apps = apps,
                )
            }.onFailure {
                _state.value = _state.value.copy(loading = false)
            }
        }
    }
}
