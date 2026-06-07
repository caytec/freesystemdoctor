package com.freesystemdoctor.android.ui.corpse

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.corpse.CorpseEntry
import com.freesystemdoctor.android.engine.corpse.CorpseReport
import com.freesystemdoctor.android.engine.history.CleanSource
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CorpseFinderUiState(
    val rootUri: Uri? = null,
    val androidMediaUri: Uri? = null,
    val report: CorpseReport = CorpseReport(emptyList(), false),
    val scanning: Boolean = false,
    val freedBytes: Long = 0L,
)

class CorpseFinderViewModel : ViewModel() {

    private val engine = ServiceLocator.corpseFinderEngine
    private val safStore = ServiceLocator.safTreeStore
    private val history = ServiceLocator.cleaningHistoryEngine

    private val _state = MutableStateFlow(CorpseFinderUiState())
    val state: StateFlow<CorpseFinderUiState> = _state.asStateFlow()

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
            _state.value = _state.value.copy(report = report, scanning = false)
        }
    }

    fun deleteAll() = delete(_state.value.report.entries)

    fun delete(entries: List<CorpseEntry>) {
        viewModelScope.launch {
            val result = engine.delete(entries)
            _state.value = _state.value.copy(
                freedBytes = _state.value.freedBytes + result.bytesFreed,
            )
            history.recordClean(CleanSource.CORPSE_FINDER, result.bytesFreed, result.itemsRemoved)
            scan()
        }
    }
}
