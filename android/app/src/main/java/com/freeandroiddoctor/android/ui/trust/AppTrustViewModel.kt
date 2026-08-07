package com.freeandroiddoctor.android.ui.trust

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.trust.TrustProgress
import com.freeandroiddoctor.android.engine.trust.TrustReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AppTrustUiState(
    val scanning: Boolean = false,
    val scanned: Boolean = false,
    val phase: TrustProgress.Phase? = null,
    val report: TrustReport? = null,
)

class AppTrustViewModel : ViewModel() {

    private val engine = ServiceLocator.appTrustEngine

    private val _state = MutableStateFlow(AppTrustUiState())
    val state: StateFlow<AppTrustUiState> = _state.asStateFlow()

    fun scan() {
        if (_state.value.scanning) return
        _state.value = AppTrustUiState(scanning = true)
        viewModelScope.launch {
            runCatching {
                engine.scan { p -> _state.update { it.copy(phase = p.phase) } }
            }
                .onSuccess {
                    _state.value = AppTrustUiState(scanning = false, scanned = true, report = it)
                }
                .onFailure {
                    _state.value = AppTrustUiState(scanning = false, scanned = true)
                }
        }
    }

    fun appDetailsIntent(pkg: String): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:$pkg")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
}
