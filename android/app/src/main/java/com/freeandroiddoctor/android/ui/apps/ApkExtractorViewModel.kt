package com.freeandroiddoctor.android.ui.apps

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.apps.BackupableApp
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ApkExtractorUiState(
    val loading: Boolean = false,
    val apps: List<BackupableApp> = emptyList(),
    val busyPackage: String? = null,
    val lastExtracted: String? = null,
    val error: String? = null,
)

class ApkExtractorViewModel : ViewModel() {

    private val engine = ServiceLocator.apkExtractorEngine
    private val _state = MutableStateFlow(ApkExtractorUiState())
    val state: StateFlow<ApkExtractorUiState> = _state.asStateFlow()

    fun load() {
        if (_state.value.loading || _state.value.apps.isNotEmpty()) return
        _state.update { it.copy(loading = true) }
        viewModelScope.launch {
            val apps = engine.listApps()
            _state.update { it.copy(loading = false, apps = apps) }
        }
    }

    fun extract(app: BackupableApp) {
        _state.update { it.copy(busyPackage = app.packageName, error = null, lastExtracted = null) }
        viewModelScope.launch {
            val result = engine.extract(app)
            _state.update {
                it.copy(
                    busyPackage = null,
                    lastExtracted = if (result.success) result.displayName else null,
                    error = if (result.success) null else (result.error ?: "error"),
                )
            }
        }
    }
}
