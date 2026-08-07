package com.freeandroiddoctor.android.ui.trackers

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.privacy.TrackerReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class TrackerUiState(
    val scanning: Boolean = false,
    val scanned: Boolean = false,
    val progress: Int = 0,
    val total: Int = 0,
    val report: TrackerReport? = null,
)

class TrackerScannerViewModel : ViewModel() {

    private val engine = ServiceLocator.trackerScannerEngine

    private val _state = MutableStateFlow(TrackerUiState())
    val state: StateFlow<TrackerUiState> = _state.asStateFlow()

    fun scan() {
        if (_state.value.scanning) return
        _state.value = TrackerUiState(scanning = true)
        viewModelScope.launch {
            runCatching {
                engine.scan { p ->
                    _state.update { it.copy(progress = p.done, total = p.total) }
                }
            }
                .onSuccess { r ->
                    _state.value = TrackerUiState(scanning = false, scanned = true, report = r)
                }
                .onFailure {
                    _state.value = TrackerUiState(scanning = false, scanned = true)
                }
        }
    }

    fun appDetailsIntent(pkg: String): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:$pkg")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
}
