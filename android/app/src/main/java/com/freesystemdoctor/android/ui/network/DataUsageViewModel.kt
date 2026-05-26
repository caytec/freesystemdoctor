package com.freesystemdoctor.android.ui.network

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.network.DataUsageItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DataUsageUiState(
    val loading: Boolean = false,
    val hasUsageAccess: Boolean = false,
    val items: List<DataUsageItem> = emptyList(),
)

class DataUsageViewModel : ViewModel() {

    private val engine = ServiceLocator.dataUsageEngine
    private val permissions = ServiceLocator.permissionManager

    private val _state = MutableStateFlow(DataUsageUiState())
    val state: StateFlow<DataUsageUiState> = _state.asStateFlow()

    fun load() {
        val granted = permissions.hasUsageAccess()
        _state.update { it.copy(hasUsageAccess = granted, loading = granted) }
        if (!granted) return
        viewModelScope.launch {
            val items = engine.usage()
            _state.update { it.copy(loading = false, items = items) }
        }
    }

    fun usageAccessIntent() = permissions.usageAccessSettingsIntent()
}
