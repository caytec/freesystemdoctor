package com.freesystemdoctor.android.ui.apps

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.apps.AuditedApp
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PermissionAuditUiState(
    val loading: Boolean = false,
    val apps: List<AuditedApp> = emptyList(),
)

class PermissionAuditViewModel : ViewModel() {

    private val engine = ServiceLocator.permissionAuditEngine
    private val appManager = ServiceLocator.appManagerEngine

    private val _state = MutableStateFlow(PermissionAuditUiState())
    val state: StateFlow<PermissionAuditUiState> = _state.asStateFlow()

    fun load() {
        if (_state.value.loading || _state.value.apps.isNotEmpty()) return
        _state.update { it.copy(loading = true) }
        viewModelScope.launch {
            val apps = engine.audit()
            _state.update { it.copy(loading = false, apps = apps) }
        }
    }

    fun appDetailsIntent(pkg: String) = appManager.appDetailsIntent(pkg)
}
