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
    fun setProvider(provider: AiProvider) = viewModelScope.launch { repo.setAiProvider(provider) }
    fun setAdvancedMode(enabled: Boolean) = viewModelScope.launch { repo.setAdvancedMode(enabled) }

    fun saveKey(key: String) {
        keyStore.setApiKey(key)
        _hasKey.value = keyStore.hasKey()
    }

    fun clearKey() {
        keyStore.clear()
        _hasKey.value = false
    }
}
