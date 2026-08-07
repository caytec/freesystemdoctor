package com.freeandroiddoctor.android.ui.apkinspect

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.privacy.ApkInspection
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ApkInspectUiState(
    val working: Boolean = false,
    val done: Boolean = false,
    val inspection: ApkInspection? = null,
    val failed: Boolean = false,
)

class ApkInspectViewModel : ViewModel() {

    private val engine = ServiceLocator.apkInspectorEngine

    private val _state = MutableStateFlow(ApkInspectUiState())
    val state: StateFlow<ApkInspectUiState> = _state.asStateFlow()

    fun inspect(uri: Uri) {
        _state.value = ApkInspectUiState(working = true)
        viewModelScope.launch {
            runCatching { engine.inspect(uri) }
                .onSuccess { result ->
                    _state.value = ApkInspectUiState(
                        working = false,
                        done = true,
                        inspection = result,
                        failed = result == null,
                    )
                }
                .onFailure {
                    _state.value = ApkInspectUiState(working = false, done = true, failed = true)
                }
        }
    }

    fun reset() {
        _state.value = ApkInspectUiState()
    }
}
