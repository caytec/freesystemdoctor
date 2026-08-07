package com.freeandroiddoctor.android.ui.photos

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.result.ScanProgress
import com.freeandroiddoctor.android.engine.media.PhotoItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PhotoReviewUiState(
    val scanning: Boolean = false,
    val scanned: Boolean = false,
    val screenshots: List<PhotoItem> = emptyList(),
    val blurry: List<PhotoItem> = emptyList(),
    val progress: ScanProgress? = null,
)

class PhotoReviewViewModel : ViewModel() {

    private val engine = ServiceLocator.blurScreenshotEngine
    private val deleteHelper = ServiceLocator.mediaDeleteHelper

    private val _state = MutableStateFlow(PhotoReviewUiState())
    val state: StateFlow<PhotoReviewUiState> = _state.asStateFlow()

    fun scan() {
        if (_state.value.scanning) return
        _state.update { it.copy(scanning = true, progress = null) }
        viewModelScope.launch {
            val review = engine.review(progress = { p -> _state.update { it.copy(progress = p) } })
            _state.update {
                it.copy(
                    scanning = false,
                    scanned = true,
                    screenshots = review.screenshots,
                    blurry = review.blurry,
                    progress = null,
                )
            }
        }
    }

    fun buildDeleteRequest(uris: List<Uri>) = deleteHelper.buildDeleteRequest(uris)
    fun onDeleted() = scan()
}
