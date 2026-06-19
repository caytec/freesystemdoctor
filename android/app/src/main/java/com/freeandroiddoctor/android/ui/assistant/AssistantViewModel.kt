package com.freeandroiddoctor.android.ui.assistant

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.ai.AiResult
import com.freeandroiddoctor.android.ai.DeviceHealthSnapshot
import com.freeandroiddoctor.android.ai.currentLocaleTag
import com.freeandroiddoctor.android.core.di.ServiceLocator
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
    /** Today's analyses used (free tier is capped; PRO is unlimited). */
    val usageToday: Int = 0,
    val limitReached: Boolean = false,
)

class AssistantViewModel : ViewModel() {

    private val ai = ServiceLocator.aiRepository
    private val settings = ServiceLocator.settingsRepository
    private val billing = ServiceLocator.billingManager
    private val _state = MutableStateFlow(AssistantUiState(hasKey = ai.hasKey()))
    val state: StateFlow<AssistantUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val used = settings.peekAiUsage(today())
            _state.value = _state.value.copy(usageToday = used)
        }
    }

    fun refreshKey() {
        _state.value = _state.value.copy(hasKey = ai.hasKey())
    }

    fun analyze() {
        if (!ai.hasKey()) {
            _state.value = _state.value.copy(error = "missing_key")
            return
        }
        viewModelScope.launch {
            // Free tier: cap at FREE_DAILY_LIMIT per day. PRO is unlimited.
            val isPro = billing.isPro.value
            if (!isPro) {
                val used = settings.peekAiUsage(today())
                if (used >= FREE_DAILY_LIMIT) {
                    _state.value = _state.value.copy(
                        limitReached = true,
                        usageToday = used,
                    )
                    return@launch
                }
            }
            _state.value = _state.value.copy(
                analyzing = true,
                error = null,
                recommendations = null,
                limitReached = false,
            )
            val snapshot = buildSnapshot()
            val provider = settings.settings.first().aiProvider
            when (val result = ai.analyze(provider, snapshot)) {
                is AiResult.Success -> {
                    val newCount = if (!isPro) settings.consumeAiUsage(today()) else _state.value.usageToday
                    _state.value = _state.value.copy(
                        analyzing = false,
                        recommendations = result.content,
                        usageToday = newCount,
                    )
                }
                is AiResult.Error ->
                    _state.value = _state.value.copy(analyzing = false, error = result.message)
            }
        }
    }

    private fun today(): String {
        val cal = java.util.Calendar.getInstance()
        return "%04d-%02d-%02d".format(
            cal.get(java.util.Calendar.YEAR),
            cal.get(java.util.Calendar.MONTH) + 1,
            cal.get(java.util.Calendar.DAY_OF_MONTH),
        )
    }

    companion object {
        const val FREE_DAILY_LIMIT = 3
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
