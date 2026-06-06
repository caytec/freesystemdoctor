package com.freesystemdoctor.android.ui.cleaner

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.cache.JunkItem
import com.freesystemdoctor.android.engine.cache.JunkReport
import com.freesystemdoctor.android.engine.history.CleanSource
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CleanerUiState(
    val scanning: Boolean = false,
    val report: JunkReport? = null,
    val lastFreedBytes: Long = 0,
)

class CleanerViewModel : ViewModel() {

    private val engine = ServiceLocator.junkEngine
    private val _state = MutableStateFlow(CleanerUiState())
    val state: StateFlow<CleanerUiState> = _state.asStateFlow()

    fun scan() {
        _state.value = _state.value.copy(scanning = true)
        viewModelScope.launch {
            val report = engine.scan()
            _state.value = _state.value.copy(scanning = false, report = report)
        }
    }

    /** Deletes this app's own cache immediately and returns freed bytes. */
    fun cleanAppCache() {
        viewModelScope.launch {
            val result = engine.cleanAppCache()
            _state.value = _state.value.copy(lastFreedBytes = result.bytesFreed)
            ServiceLocator.cleaningHistoryEngine.recordClean(
                CleanSource.JUNK_CACHE,
                result.bytesFreed,
                result.itemsRemoved,
            )
            scan()
        }
    }

    fun mediaUris(): List<android.net.Uri> =
        _state.value.report?.mediaItems?.map(JunkItem::uri).orEmpty()

    fun buildDeleteRequest() = engine.buildDeleteRequest(mediaUris())

    fun onMediaDeleted() = scan()
}
