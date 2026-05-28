package com.freesystemdoctor.android.ui.trash

import android.app.PendingIntent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.trash.TrashedItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class TrashUiState(
    val items: List<TrashedItem> = emptyList(),
    val isLoading: Boolean = true,
    val selected: Set<android.net.Uri> = emptySet(),
)

class TrashViewModel : ViewModel() {

    private val engine = ServiceLocator.trashEngine

    private val _state = MutableStateFlow(TrashUiState())
    val state: StateFlow<TrashUiState> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            val items = engine.listTrashed()
            _state.value = TrashUiState(items = items, isLoading = false, selected = emptySet())
        }
    }

    fun toggle(uri: android.net.Uri) {
        val current = _state.value.selected
        _state.value = _state.value.copy(
            selected = if (uri in current) current - uri else current + uri,
        )
    }

    fun selectAll() {
        _state.value = _state.value.copy(selected = _state.value.items.map { it.uri }.toSet())
    }

    fun restoreRequest(): PendingIntent? =
        engine.buildRestoreRequest(_state.value.selected.toList())

    fun deleteRequest(): PendingIntent? =
        engine.buildPermanentDeleteRequest(_state.value.selected.toList())
}
