package com.freesystemdoctor.android.ui.cache

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.cache.HiddenCacheItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class HiddenCacheUiState(
    val treeUri: Uri? = null,
    val items: List<HiddenCacheItem> = emptyList(),
    val scanning: Boolean = false,
    val freedBytes: Long = 0L,
)

class HiddenCacheViewModel : ViewModel() {

    private val engine = ServiceLocator.hiddenCacheEngine
    private val store = ServiceLocator.safTreeStore

    private val _state = MutableStateFlow(HiddenCacheUiState())
    val state: StateFlow<HiddenCacheUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            store.androidMediaTreeUri.collect { uri ->
                _state.value = _state.value.copy(treeUri = uri)
                if (uri != null) scan()
            }
        }
    }

    fun onTreeGranted(uri: Uri) {
        viewModelScope.launch { store.persistAndroidMedia(uri) }
    }

    fun scan() {
        val uri = _state.value.treeUri ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(scanning = true)
            val items = engine.scan(uri)
            _state.value = _state.value.copy(items = items, scanning = false)
        }
    }

    fun clean(item: HiddenCacheItem) {
        viewModelScope.launch {
            val result = engine.clean(item.folderUri)
            _state.value = _state.value.copy(
                freedBytes = _state.value.freedBytes + result.bytesFreed,
            )
            scan()
        }
    }
}
