package com.freeandroiddoctor.android.ui.photos

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.media.PhotoItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CompressUiState(
    val loading: Boolean = false,
    val photos: List<PhotoItem> = emptyList(),
    val busyUri: String? = null,
    val savedTotal: Long = 0,
    val lastMessage: String? = null,
)

class CompressViewModel : ViewModel() {

    private val largeFiles = ServiceLocator.largeFilesEngine
    private val engine = ServiceLocator.imageCompressionEngine

    private val _state = MutableStateFlow(CompressUiState())
    val state: StateFlow<CompressUiState> = _state.asStateFlow()

    fun load() {
        if (_state.value.loading || _state.value.photos.isNotEmpty()) return
        _state.update { it.copy(loading = true) }
        viewModelScope.launch {
            val photos = largeFiles.findLargeFiles(minBytes = 1L * 1024 * 1024)
                .filter { it.mimeType.startsWith("image/") }
                .map { PhotoItem(it.uri, it.displayName, it.sizeBytes) }
            _state.update { it.copy(loading = false, photos = photos) }
        }
    }

    fun compress(item: PhotoItem) {
        _state.update { it.copy(busyUri = item.uri.toString(), lastMessage = null) }
        viewModelScope.launch {
            val result = engine.compress(item)
            _state.update {
                it.copy(
                    busyUri = null,
                    savedTotal = it.savedTotal + if (result.success) result.savedBytes else 0,
                    lastMessage = if (result.success) result.name else null,
                )
            }
        }
    }
}
