package com.freeandroiddoctor.android.ui.apps

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.apps.AppUsageItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AppUsageUiState(
    val loading: Boolean = false,
    val hasUsageAccess: Boolean = false,
    val items: List<AppUsageItem> = emptyList(),
)

class AppUsageViewModel : ViewModel() {

    private val engine = ServiceLocator.appUsageEngine
    private val permissions = ServiceLocator.permissionManager

    private val _state = MutableStateFlow(AppUsageUiState())
    val state: StateFlow<AppUsageUiState> = _state.asStateFlow()

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
