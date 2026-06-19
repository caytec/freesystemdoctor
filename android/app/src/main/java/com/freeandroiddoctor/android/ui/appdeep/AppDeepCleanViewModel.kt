package com.freeandroiddoctor.android.ui.appdeep

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.appdeep.AppDeepReport
import com.freeandroiddoctor.android.engine.appdeep.DeepHit
import com.freeandroiddoctor.android.engine.appdeep.Safety
import com.freeandroiddoctor.android.engine.history.CleanSource
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AppDeepUiState(
    val rootUri: Uri? = null,
    val androidMediaUri: Uri? = null,
    val report: AppDeepReport = AppDeepReport(emptyMap()),
    val scanning: Boolean = false,
    val selected: Set<String> = emptySet(), // folderUri strings
    val freedBytes: Long = 0L,
)

class AppDeepCleanViewModel : ViewModel() {

    private val engine = ServiceLocator.appDeepCleanEngine
    private val safStore = ServiceLocator.safTreeStore
    private val history = ServiceLocator.cleaningHistoryEngine

    private val _state = MutableStateFlow(AppDeepUiState())
    val state: StateFlow<AppDeepUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            safStore.treeUri.collect { uri ->
                _state.value = _state.value.copy(rootUri = uri)
                if (uri != null) scan()
            }
        }
        viewModelScope.launch {
            safStore.androidMediaTreeUri.collect { uri ->
                _state.value = _state.value.copy(androidMediaUri = uri)
            }
        }
    }

    fun onRootGranted(uri: Uri) {
        viewModelScope.launch { safStore.persist(uri) }
    }

    fun scan() {
        viewModelScope.launch {
            val roots = listOfNotNull(_state.value.rootUri, _state.value.androidMediaUri).distinct()
            if (roots.isEmpty()) return@launch
            _state.value = _state.value.copy(scanning = true)
            val report = engine.scan(roots)
            // Auto-select SAFE + CAUTIOUS; OPT_IN starts unchecked.
            val preselected = report.perApp.values
                .flatMap { it.hits }
                .filter { it.rule.safety != Safety.OPT_IN }
                .map { it.folderUri.toString() }
                .toSet()
            _state.value = _state.value.copy(
                report = report,
                scanning = false,
                selected = preselected,
            )
        }
    }

    fun toggle(hit: DeepHit) {
        val key = hit.folderUri.toString()
        val current = _state.value.selected
        _state.value = _state.value.copy(
            selected = if (key in current) current - key else current + key,
        )
    }

    fun cleanSelected() {
        viewModelScope.launch {
            val selected = _state.value.selected
            val hits = _state.value.report.perApp.values
                .flatMap { it.hits }
                .filter { it.folderUri.toString() in selected }
            if (hits.isEmpty()) return@launch
            val result = engine.clean(hits)
            _state.value = _state.value.copy(
                freedBytes = _state.value.freedBytes + result.bytesFreed,
            )
            history.recordClean(CleanSource.APP_DEEP_CLEAN, result.bytesFreed, result.itemsRemoved)
            scan()
        }
    }
}
