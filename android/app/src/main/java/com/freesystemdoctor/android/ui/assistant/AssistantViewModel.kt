package com.freesystemdoctor.android.ui.assistant

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.ai.AiResult
import com.freesystemdoctor.android.ai.DeviceHealthSnapshot
import com.freesystemdoctor.android.ai.currentLocaleTag
import com.freesystemdoctor.android.core.di.ServiceLocator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class AssistantUiState(
    val hasKey: Boolean = false,
    val analyzing: Boolean = false,
    val recommendations: String? = null,
    val error: String? = null,
)

class AssistantViewModel : ViewModel() {

    private val ai = ServiceLocator.aiRepository
    private val settings = ServiceLocator.settingsRepository
    private val _state = MutableStateFlow(AssistantUiState(hasKey = ai.hasKey()))
    val state: StateFlow<AssistantUiState> = _state.asStateFlow()

    fun refreshKey() {
        _state.value = _state.value.copy(hasKey = ai.hasKey())
    }

    fun analyze() {
        if (!ai.hasKey()) {
            _state.value = _state.value.copy(error = "missing_key")
            return
        }
        _state.value = _state.value.copy(analyzing = true, error = null, recommendations = null)
        viewModelScope.launch {
            val snapshot = buildSnapshot()
            val provider = settings.settings.first().aiProvider
            when (val result = ai.analyze(provider, snapshot)) {
                is AiResult.Success ->
                    _state.value = _state.value.copy(analyzing = false, recommendations = result.content)
                is AiResult.Error ->
                    _state.value = _state.value.copy(analyzing = false, error = result.message)
            }
        }
    }

    private suspend fun buildSnapshot(): DeviceHealthSnapshot = withContext(Dispatchers.IO) {
        val volume = ServiceLocator.storageEngine.readPrimaryVolume()
        val memory = ServiceLocator.memoryEngine.read()
        val battery = ServiceLocator.batteryEngine.read()
        val junk = ServiceLocator.junkEngine.scan()
        val apps = ServiceLocator.storageEngine.readPerApp().take(5)
        DeviceHealthSnapshot(
            storageTotalBytes = volume.totalBytes,
            storageFreeBytes = volume.freeBytes,
            ramTotalBytes = memory.totalBytes,
            ramAvailableBytes = memory.availableBytes,
            batteryPercent = battery.levelPercent,
            batteryTemperatureCelsius = battery.temperatureCelsius,
            reclaimableJunkBytes = junk.reclaimableBytes,
            largestApps = apps.map { it.label to it.totalBytes },
            locale = currentLocaleTag(),
        )
    }
}
