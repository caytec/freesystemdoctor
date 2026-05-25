package com.freesystemdoctor.android.ui.apps

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.apps.AppListItem
import com.freesystemdoctor.android.engine.apps.AppSort
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AppsUiState(
    val loading: Boolean = false,
    val apps: List<AppListItem> = emptyList(),
    val includeSystem: Boolean = false,
    val sort: AppSort = AppSort.SIZE,
)

class AppsViewModel : ViewModel() {

    private val engine = ServiceLocator.appManagerEngine
    private val _state = MutableStateFlow(AppsUiState())
    val state: StateFlow<AppsUiState> = _state.asStateFlow()

    fun load() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            val s = _state.value
            val apps = engine.listApps(s.includeSystem, s.sort)
            _state.value = _state.value.copy(loading = false, apps = apps)
        }
    }

    fun toggleSystem() {
        _state.value = _state.value.copy(includeSystem = !_state.value.includeSystem)
        load()
    }

    fun setSort(sort: AppSort) {
        _state.value = _state.value.copy(sort = sort)
        load()
    }

    fun uninstallIntent(pkg: String) = engine.uninstallIntent(pkg)
    fun appDetailsIntent(pkg: String) = engine.appDetailsIntent(pkg)
}
