package com.freeandroiddoctor.android.ui.files

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.files.EmptyFolder
import com.freeandroiddoctor.android.engine.files.FolderEntry
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class FolderToolsUiState(
    val treeUri: Uri? = null,
    val loading: Boolean = false,
    val totalBytes: Long = 0,
    val children: List<FolderEntry> = emptyList(),
    val emptyFolders: List<EmptyFolder> = emptyList(),
    val findingEmpty: Boolean = false,
)

class FolderToolsViewModel : ViewModel() {

    private val store = ServiceLocator.safTreeStore
    private val engine = ServiceLocator.safTreeEngine

    private val _state = MutableStateFlow(FolderToolsUiState())
    val state: StateFlow<FolderToolsUiState> = _state.asStateFlow()

    fun load() {
        viewModelScope.launch {
            val uri = store.current()
            _state.update { it.copy(treeUri = uri) }
            if (uri != null) scan(uri)
        }
    }

    fun onTreeGranted(uri: Uri) {
        viewModelScope.launch {
            store.persist(uri)
            _state.update { it.copy(treeUri = uri, emptyFolders = emptyList()) }
            scan(uri)
        }
    }

    private fun scan(uri: Uri) {
        _state.update { it.copy(loading = true) }
        viewModelScope.launch {
            val children = engine.listChildren(uri)
            val total = engine.totalSize(uri)
            _state.update { it.copy(loading = false, children = children, totalBytes = total) }
        }
    }

    fun findEmpty() {
        val uri = _state.value.treeUri ?: return
        _state.update { it.copy(findingEmpty = true) }
        viewModelScope.launch {
            val empties = engine.findEmptyFolders(uri)
            _state.update { it.copy(findingEmpty = false, emptyFolders = empties) }
        }
    }

    fun deleteEmpty(uri: Uri) {
        viewModelScope.launch {
            if (engine.delete(uri)) {
                _state.update { s -> s.copy(emptyFolders = s.emptyFolders.filterNot { it.uri == uri }) }
            }
        }
    }
}
