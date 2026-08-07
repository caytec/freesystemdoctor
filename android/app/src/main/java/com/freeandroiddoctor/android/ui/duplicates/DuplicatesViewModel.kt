package com.freeandroiddoctor.android.ui.duplicates

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.result.ScanProgress
import com.freeandroiddoctor.android.engine.duplicates.DuplicateGroup
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DuplicatesUiState(
    val scanning: Boolean = false,
    val scanned: Boolean = false,
    val audioOnly: Boolean = false,
    val groups: List<DuplicateGroup> = emptyList(),
    val progress: ScanProgress? = null,
) {
    val reclaimableBytes: Long get() = groups.sumOf { it.reclaimableBytes }
}

class DuplicatesViewModel : ViewModel() {

    private val engine = ServiceLocator.duplicateEngine
    private val deleteHelper = ServiceLocator.mediaDeleteHelper

    private val _state = MutableStateFlow(DuplicatesUiState())
    val state: StateFlow<DuplicatesUiState> = _state.asStateFlow()

    fun setAudioOnly(value: Boolean) {
        _state.update { it.copy(audioOnly = value) }
    }

    fun scan() {
        if (_state.value.scanning) return
        val mime = if (_state.value.audioOnly) "audio/" else null
        _state.update { it.copy(scanning = true, progress = null) }
        viewModelScope.launch {
            val groups = engine.findDuplicates(mimePrefix = mime, progress = { p ->
                _state.update { it.copy(progress = p) }
            })
            _state.update {
                it.copy(scanning = false, scanned = true, groups = groups, progress = null)
            }
        }
    }

    /** Keeps the largest copy in each group, deletes the rest. */
    fun deletableUris(): List<Uri> =
        _state.value.groups.flatMap { group -> group.files.drop(1).map { it.uri } }

    fun buildDeleteRequest() = deleteHelper.buildDeleteRequest(deletableUris())

    fun onDeleted() = scan()
}
