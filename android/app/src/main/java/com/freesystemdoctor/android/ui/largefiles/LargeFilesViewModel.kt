package com.freesystemdoctor.android.ui.largefiles

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.largefiles.MediaFile
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LargeFilesUiState(
    val scanning: Boolean = false,
    val scanned: Boolean = false,
    val videosOnly: Boolean = false,
    val files: List<MediaFile> = emptyList(),
) {
    val totalBytes: Long get() = files.sumOf { it.sizeBytes }
}

class LargeFilesViewModel : ViewModel() {

    private val engine = ServiceLocator.largeFilesEngine
    private val deleteHelper = ServiceLocator.mediaDeleteHelper

    private val _state = MutableStateFlow(LargeFilesUiState())
    val state: StateFlow<LargeFilesUiState> = _state.asStateFlow()

    fun setVideosOnly(value: Boolean) {
        _state.update { it.copy(videosOnly = value) }
    }

    fun scan() {
        if (_state.value.scanning) return
        val videos = _state.value.videosOnly
        _state.update { it.copy(scanning = true) }
        viewModelScope.launch {
            val files = engine.findLargeFiles(
                minBytes = if (videos) 20L * 1024 * 1024 else 50L * 1024 * 1024,
                mimePrefix = if (videos) "video/" else null,
            )
            _state.update { it.copy(scanning = false, scanned = true, files = files) }
        }
    }

    fun buildDeleteRequest(uris: List<Uri>) = deleteHelper.buildDeleteRequest(uris)

    fun onDeleted() = scan()
}
