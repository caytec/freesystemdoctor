package com.freesystemdoctor.android.ui.lock

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.apps.AppListItem
import com.freesystemdoctor.android.engine.apps.AppSort
import com.freesystemdoctor.android.service.AppLockService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class AppLockUiState(
    val apps: List<AppListItem> = emptyList(),
    val loading: Boolean = true,
    val hasUsageAccess: Boolean = false,
    val hasOverlay: Boolean = false,
)

class AppLockViewModel(application: Application) : AndroidViewModel(application) {

    private val engine = ServiceLocator.appLockEngine
    private val appManager = ServiceLocator.appManagerEngine
    private val permissions = ServiceLocator.permissionManager

    private val _state = MutableStateFlow(AppLockUiState())
    val state: StateFlow<AppLockUiState> = _state.asStateFlow()

    val enabled: StateFlow<Boolean> =
        engine.enabled.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)
    val lockedPackages: StateFlow<Set<String>> =
        engine.lockedPackages.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptySet())

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = AppLockUiState(loading = true)
            val apps = appManager.listApps(includeSystem = false, sort = AppSort.NAME)
            _state.value = AppLockUiState(
                apps = apps,
                loading = false,
                hasUsageAccess = permissions.hasUsageAccess(),
                hasOverlay = engine.canDrawOverlays(),
            )
        }
    }

    fun setEnabled(value: Boolean) {
        val ctx = getApplication<Application>()
        viewModelScope.launch {
            engine.setEnabled(value)
            if (value) AppLockService.start(ctx) else AppLockService.stop(ctx)
        }
    }

    fun toggle(pkg: String) {
        viewModelScope.launch { engine.toggleLocked(pkg) }
    }

    fun usageAccessIntent() = permissions.usageAccessSettingsIntent()
    fun overlayIntent() = engine.overlaySettingsIntent()
}
