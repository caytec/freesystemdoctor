package com.freesystemdoctor.android.ui.cloudbackup

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.data.settings.AppSettings
import com.freesystemdoctor.android.engine.cloudbackup.BackupEstimate
import com.freesystemdoctor.android.engine.cloudbackup.BackupOptions
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class CloudBackupUiState(
    val running: Boolean = false,
    val lastResult: String? = null,
    val estimate: BackupEstimate? = null,
    val error: String? = null,
)

class CloudBackupViewModel(application: Application) : AndroidViewModel(application) {

    private val engine = ServiceLocator.cloudBackupEngine
    private val safStore = ServiceLocator.safTreeStore
    private val settings = ServiceLocator.settingsRepository
    private val scheduler = ServiceLocator.workScheduler
    private val keyStore = ServiceLocator.cloudBackupKeyStore

    private val _state = MutableStateFlow(CloudBackupUiState())
    val state: StateFlow<CloudBackupUiState> = _state.asStateFlow()

    val backupFolder: StateFlow<Uri?> =
        safStore.backupTreeUri.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    fun setFolder(uri: Uri) {
        viewModelScope.launch { safStore.persistBackup(uri) }
    }

    fun saveScheduledPassphrase(passphrase: String) {
        keyStore.write(passphrase)
        scheduler.setCloudBackupSchedule(true)
    }

    fun cancelSchedule() {
        keyStore.clear()
        scheduler.setCloudBackupSchedule(false)
    }

    fun estimate(options: BackupOptions) {
        viewModelScope.launch {
            val s = settings.settings.first()
            _state.value = _state.value.copy(estimate = engine.estimate(options, s))
        }
    }

    fun runNow(passphrase: String, options: BackupOptions) {
        viewModelScope.launch {
            val folder = backupFolder.value ?: return@launch
            val s = settings.settings.first()
            _state.value = _state.value.copy(running = true, error = null)
            runCatching {
                engine.runBackup(folder, passphrase.toCharArray(), options, s).also {
                    engine.rotateOlder(folder, keep = 5)
                }
            }
                .onSuccess { result ->
                    _state.value = CloudBackupUiState(running = false, lastResult = result.fileName)
                }
                .onFailure { error ->
                    _state.value = CloudBackupUiState(
                        running = false,
                        error = error.localizedMessage ?: "failed",
                    )
                }
        }
    }
}
