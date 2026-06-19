package com.freeandroiddoctor.android.ui.backup

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.contacts.DuplicateContact
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class BackupUiState(
    val hasContacts: Boolean = false,
    val hasSms: Boolean = false,
    val duplicates: List<DuplicateContact> = emptyList(),
    val working: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false,
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
            _state.update { it.copy(duplicates = contacts.findDuplicates()) }
        }
    }

    fun exportContacts() {
        _state.update { it.copy(working = true, message = null) }
        viewModelScope.launch {
            val result = contacts.exportVCard()
            _state.update {
                it.copy(
                    working = false,
                    isError = !result.success,
                    message = if (result.success) {
                        "${result.fileName} (${result.count})"
                    } else {
                        result.error
                    },
                )
            }
        }
    }

    fun exportSms() {
        _state.update { it.copy(working = true, message = null) }
        viewModelScope.launch {
            val result = sms.export()
            _state.update {
                it.copy(
                    working = false,
                    isError = !result.success,
                    message = if (result.success) {
                        "${result.fileName} (${result.count})"
                    } else {
                        result.error
                    },
                )
            }
        }
    }
}
