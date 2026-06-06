package com.freesystemdoctor.android.ui.history

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.history.HistorySummary
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CleaningHistoryUi(
    val loading: Boolean = true,
    val summary: HistorySummary? = null,
    val exportSuccess: Int? = null,
    val exportError: String? = null,
)

class CleaningHistoryViewModel(app: Application) : AndroidViewModel(app) {

    private val engine = ServiceLocator.cleaningHistoryEngine
    private val billing = ServiceLocator.billingManager

    private val _ui = MutableStateFlow(CleaningHistoryUi())
    val ui: StateFlow<CleaningHistoryUi> = _ui.asStateFlow()

    val isPro: StateFlow<Boolean> = billing.isPro

    init {
        load()
        viewModelScope.launch {
            engine.changes.collect { load() }
        }
    }

    fun load() {
        viewModelScope.launch {
            _ui.value = _ui.value.copy(loading = true)
            val s = engine.summary()
            _ui.value = _ui.value.copy(loading = false, summary = s)
        }
    }

    fun exportCsv(target: Uri) {
        viewModelScope.launch {
            runCatching { engine.exportCsv(getApplication(), target) }
                .onSuccess { count -> _ui.value = _ui.value.copy(exportSuccess = count) }
                .onFailure { e ->
                    _ui.value = _ui.value.copy(exportError = e.message ?: "export failed")
                }
        }
    }

    fun clearExportMessages() {
        _ui.value = _ui.value.copy(exportSuccess = null, exportError = null)
    }
}
