package com.freesystemdoctor.android.ui.apps

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.apps.RarelyUsedApp
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class RarelyUsedUiState(
    val loading: Boolean = false,
    val hasUsageAccess: Boolean = false,
    val apps: List<RarelyUsedApp> = emptyList(),
)

class RarelyUsedViewModel : ViewModel() {

    private val engine = ServiceLocator.rarelyUsedEngine
    private val appManager = ServiceLocator.appManagerEngine
    private val permissions = ServiceLocator.permissionManager

    private val _state = MutableStateFlow(RarelyUsedUiState())
    val state: StateFlow<RarelyUsedUiState> = _state.asStateFlow()

    fun load() {
        val granted = permissions.hasUsageAccess()
        _state.update { it.copy(hasUsageAccess = granted, loading = granted) }
        if (!granted) return
        viewModelScope.launch {
            val apps = engine.rarelyUsed()
            _state.update { it.copy(loading = false, apps = apps) }
        }
    }

    fun usageAccessIntent() = permissions.usageAccessSettingsIntent()
    fun uninstallIntent(pkg: String) = appManager.uninstallIntent(pkg)
    fun appDetailsIntent(pkg: String) = appManager.appDetailsIntent(pkg)
}
