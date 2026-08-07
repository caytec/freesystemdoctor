package com.freeandroiddoctor.android.ui.posture

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.privacy.PostureReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PostureUiState(
    val loading: Boolean = true,
    val report: PostureReport? = null,
)

class PostureViewModel : ViewModel() {

    private val engine = ServiceLocator.securityPostureEngine

    private val _state = MutableStateFlow(PostureUiState())
    val state: StateFlow<PostureUiState> = _state.asStateFlow()

    fun load() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            runCatching { engine.scan() }
                .onSuccess { _state.value = PostureUiState(false, it) }
                .onFailure { _state.value = _state.value.copy(loading = false) }
        }
    }

    fun appDetailsIntent(pkg: String): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:$pkg")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
}
