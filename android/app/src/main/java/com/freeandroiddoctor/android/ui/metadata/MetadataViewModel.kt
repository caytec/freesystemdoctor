package com.freeandroiddoctor.android.ui.metadata

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.media.StripOutcome
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MetadataUiState(
    val working: Boolean = false,
    val processed: Int = 0,
    val total: Int = 0,
    val currentName: String = "",
    val outcomes: List<StripOutcome> = emptyList(),
    val done: Boolean = false,
) {
    val cleaned: Int get() = outcomes.count { it.success }
    val withLocation: Int get() = outcomes.count { it.success && it.hadLocation }
    val failed: Int get() = outcomes.count { !it.success }
}

class MetadataViewModel : ViewModel() {

    private val engine = ServiceLocator.metadataStripperEngine

    private val _state = MutableStateFlow(MetadataUiState())
    val state: StateFlow<MetadataUiState> = _state.asStateFlow()

    fun strip(uris: List<Uri>) {
        if (uris.isEmpty() || _state.value.working) return
        _state.value = MetadataUiState(working = true, total = uris.size)
        viewModelScope.launch {
            val outcomes = engine.stripAll(uris) { p ->
                _state.update {
                    it.copy(processed = p.done, total = p.total, currentName = p.currentName)
                }
            }
            _state.update {
                it.copy(
                    working = false,
                    done = true,
                    processed = outcomes.size,
                    outcomes = outcomes,
                )
            }
        }
    }

    fun reset() {
        _state.value = MetadataUiState()
    }
}
