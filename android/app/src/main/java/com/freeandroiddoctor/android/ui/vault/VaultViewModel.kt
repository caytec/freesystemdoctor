package com.freeandroiddoctor.android.ui.vault

import android.app.Application
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.vault.VaultEntry
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class VaultUiState(
    val unlocked: Boolean = false,
    val entries: List<VaultEntry> = emptyList(),
    val busy: Boolean = false,
    val pendingExport: VaultEntry? = null,
    val message: String? = null,
)

class VaultViewModel(application: Application) : AndroidViewModel(application) {

    private val engine = ServiceLocator.appVaultEngine

    private val _state = MutableStateFlow(VaultUiState())
    val state: StateFlow<VaultUiState> = _state.asStateFlow()

    fun onUnlocked() {
        _state.value = _state.value.copy(unlocked = true)
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(busy = true)
            _state.value = _state.value.copy(entries = engine.list(), busy = false)
        }
    }

    fun add(source: Uri) {
        viewModelScope.launch {
            _state.value = _state.value.copy(busy = true)
            val ctx = getApplication<Application>()
            val (name, mime) = readMeta(ctx, source)
            engine.add(source, name, mime)
            refresh()
        }
    }

    fun queueExport(entry: VaultEntry) {
        _state.value = _state.value.copy(pendingExport = entry)
    }

    fun consumePendingExport(): VaultEntry? {
        val e = _state.value.pendingExport
        _state.value = _state.value.copy(pendingExport = null)
        return e
    }

    fun export(entryId: String, destination: Uri) {
        viewModelScope.launch {
            val ok = engine.export(entryId, destination)
            _state.value = _state.value.copy(message = if (ok) "ok" else "err")
        }
    }

    fun delete(entry: VaultEntry) {
        viewModelScope.launch {
            engine.delete(entry.id)
            refresh()
        }
    }

    private fun readMeta(ctx: android.content.Context, source: Uri): Pair<String, String> {
        var name = "vault-file"
        var mime = ctx.contentResolver.getType(source) ?: "application/octet-stream"
        ctx.contentResolver.query(source, null, null, null, null)?.use { c ->
            val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && c.moveToFirst()) {
                c.getString(idx)?.let { name = it }
            }
        }
        return name to mime
    }
}
