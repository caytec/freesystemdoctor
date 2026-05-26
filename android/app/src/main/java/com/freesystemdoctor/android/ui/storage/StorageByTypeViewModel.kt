package com.freesystemdoctor.android.ui.storage

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.media.CategoryUsage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class StorageByTypeUiState(
    val loading: Boolean = false,
    val categories: List<CategoryUsage> = emptyList(),
) {
    val maxBytes: Long get() = categories.maxOfOrNull { it.totalBytes } ?: 1L
}

class StorageByTypeViewModel : ViewModel() {

    private val engine = ServiceLocator.mediaCategoryEngine
    private val _state = MutableStateFlow(StorageByTypeUiState())
    val state: StateFlow<StorageByTypeUiState> = _state.asStateFlow()

    fun load() {
        if (_state.value.loading) return
        _state.update { it.copy(loading = true) }
        viewModelScope.launch {
            val categories = engine.scan()
            _state.update { it.copy(loading = false, categories = categories) }
        }
    }
}
