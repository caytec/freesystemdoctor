package com.freeandroiddoctor.android.ui.backup

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.contacts.DuplicateContact
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Which export the user started, so we know what to do once they pick a file. */
enum class ExportKind { CONTACTS, SMS }

data class BackupUiState(
    val hasContacts: Boolean = false,
    val hasSms: Boolean = false,
    val duplicates: List<DuplicateContact> = emptyList(),
    val working: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false,
    /** Non-null while the passphrase sheet is open for the given export. */
    val pendingKind: ExportKind? = null,
)

class BackupViewModel : ViewModel() {

    private val contacts = ServiceLocator.contactsEngine
    private val sms = ServiceLocator.smsBackupEngine

    private val _state = MutableStateFlow(BackupUiState())
    val state: StateFlow<BackupUiState> = _state.asStateFlow()

    fun refresh() {
        _state.update {
            it.copy(hasContacts = contacts.hasPermission(), hasSms = sms.hasPermission())
        }
        if (contacts.hasPermission()) loadDuplicates()
    }

    private fun loadDuplicates() {
        viewModelScope.launch {
            runCatching { contacts.findDuplicates() }
                .onSuccess { list -> _state.update { it.copy(duplicates = list) } }
        }
    }

    /** Step 1: user tapped Export — ask for a passphrase before touching any data. */
    fun startExport(kind: ExportKind) {
        _state.update { it.copy(pendingKind = kind, message = null, isError = false) }
    }

    fun cancelExport() {
        _state.update { it.copy(pendingKind = null) }
    }

    fun suggestedFileName(kind: ExportKind): String = when (kind) {
        ExportKind.CONTACTS -> contacts.suggestedFileName()
        ExportKind.SMS -> sms.suggestedFileName()
    }

    /**
     * Step 2: the user picked a destination and set a passphrase. [passphrase] is
     * wiped by the engine once the archive is written.
     */
    fun runExport(kind: ExportKind, target: Uri, passphrase: CharArray) {
        _state.update { it.copy(working = true, message = null, pendingKind = null) }
        viewModelScope.launch {
            val (ok, label, error) = when (kind) {
                ExportKind.CONTACTS -> contacts.exportEncrypted(target, passphrase)
                    .let { Triple(it.success, "${it.fileName} (${it.count})", it.error) }
                ExportKind.SMS -> sms.exportEncrypted(target, passphrase)
                    .let { Triple(it.success, "${it.fileName} (${it.count})", it.error) }
            }
            _state.update {
                it.copy(working = false, isError = !ok, message = if (ok) label else error)
            }
        }
    }
}
