package com.freesystemdoctor.android.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.ai.AiProvider
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.data.settings.AppSettings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class SettingsViewModel : ViewModel() {

    private val repo = ServiceLocator.settingsRepository
    private val keyStore = ServiceLocator.aiKeyStore()

    val settings: StateFlow<AppSettings> = repo.settings.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = AppSettings(),
    )

    private val _hasKey = MutableStateFlow(keyStore.hasKey())
    val hasKey: StateFlow<Boolean> = _hasKey.asStateFlow()

    fun setDarkTheme(enabled: Boolean) = viewModelScope.launch { repo.setDarkTheme(enabled) }
    fun setFollowSystem(enabled: Boolean) = viewModelScope.launch { repo.setFollowSystem(enabled) }
    fun setProvider(provider: AiProvider) = viewModelScope.launch { repo.setAiProvider(provider) }
    fun setAdvancedMode(enabled: Boolean) = viewModelScope.launch { repo.setAdvancedMode(enabled) }
    fun setScheduledCleaning(enabled: Boolean) = viewModelScope.launch { repo.setScheduledCleaning(enabled) }
    fun setMonitorEnabled(enabled: Boolean) = viewModelScope.launch { repo.setMonitorEnabled(enabled) }

    fun setShizukuEnabled(enabled: Boolean) = viewModelScope.launch {
        repo.setShizukuEnabled(enabled)
        if (enabled) ServiceLocator.shizukuManager.requestPermission()
    }

    /** Stable label for the Settings screen — keeps Compose pure of context lookups. */
    fun shizukuStatusLabel(): String = when (ServiceLocator.shizukuManager.status()) {
        com.freesystemdoctor.android.core.shizuku.ShizukuManager.Status.Granted -> "Granted ✓"
        com.freesystemdoctor.android.core.shizuku.ShizukuManager.Status.Denied -> "Denied"
        com.freesystemdoctor.android.core.shizuku.ShizukuManager.Status.Unavailable -> "Not installed or not running"
    }

    fun saveKey(key: String) {
        keyStore.setApiKey(key)
        _hasKey.value = keyStore.hasKey()
    }

    fun clearKey() {
        keyStore.clear()
        _hasKey.value = false
    }
}
