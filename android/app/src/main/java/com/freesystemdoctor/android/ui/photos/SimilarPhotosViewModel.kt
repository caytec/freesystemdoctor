package com.freesystemdoctor.android.ui.photos

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.core.result.ScanProgress
import com.freesystemdoctor.android.engine.media.SimilarGroup
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SimilarPhotosUiState(
    val scanning: Boolean = false,
    val scanned: Boolean = false,
    val groups: List<SimilarGroup> = emptyList(),
    val progress: ScanProgress? = null,
) {
    val reclaimableBytes: Long get() = groups.sumOf { it.reclaimableBytes }
}

class SimilarPhotosViewModel : ViewModel() {

    private val engine = ServiceLocator.similarPhotoEngine
    private val deleteHelper = ServiceLocator.mediaDeleteHelper

    private val _state = MutableStateFlow(SimilarPhotosUiState())
    val state: StateFlow<SimilarPhotosUiState> = _state.asStateFlow()

    fun scan() {
        if (_state.value.scanning) return
        _state.update { it.copy(scanning = true, progress = null) }
        viewModelScope.launch {
            val groups = engine.findSimilar(progress = { p -> _state.update { it.copy(progress = p) } })
            _state.update { it.copy(scanning = false, scanned = true, groups = groups, progress = null) }
        }
    }

    /** Keeps the largest photo in each group. */
    fun deletableUris(): List<Uri> =
        _state.value.groups.flatMap { group -> group.items.drop(1).map { it.uri } }

    fun buildDeleteRequest() = deleteHelper.buildDeleteRequest(deletableUris())

    fun onDeleted() = scan()
}
