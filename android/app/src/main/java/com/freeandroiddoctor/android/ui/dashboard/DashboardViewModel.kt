package com.freeandroiddoctor.android.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.battery.BatteryInfo
import com.freeandroiddoctor.android.engine.device.DeviceInfo
import com.freeandroiddoctor.android.engine.memory.MemoryInfo
import com.freeandroiddoctor.android.engine.privacy.NetworkPrivacyReport
import com.freeandroiddoctor.android.engine.storage.VolumeInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class DashboardUiState(
    val loading: Boolean = true,
    val volume: VolumeInfo? = null,
    val memory: MemoryInfo? = null,
    val battery: BatteryInfo? = null,
    val device: DeviceInfo? = null,
    val healthScore: Int = 0,
    val networkPrivacy: NetworkPrivacyReport? = null,
    val activeModeId: String? = null,
)

class DashboardViewModel : ViewModel() {

    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            // All reads run on IO (BatteryEngine.read does a registerReceiver +
            // binder calls; MemoryEngine/DeviceInfo also touch the platform) so the
            // first frame isn't blocked on the main thread. Each source degrades to
            // null independently — one failing call can't crash the dashboard or
            // hang the refresh spinner.
            val next = withContext(Dispatchers.IO) {
                val volume = runCatching { ServiceLocator.storageEngine.readPrimaryVolume() }.getOrNull()
                val memory = runCatching { ServiceLocator.memoryEngine.read() }.getOrNull()
                val battery = runCatching { ServiceLocator.batteryEngine.read() }.getOrNull()
                val device = runCatching { ServiceLocator.deviceInfoEngine.read() }.getOrNull()
                val network = runCatching { ServiceLocator.networkPrivacyEngine.snapshot() }.getOrNull()
                val activeMode = runCatching {
                    ServiceLocator.modeStore.activeSnapshotOnce()?.activeModeId
                }.getOrNull()
                DashboardUiState(
                    loading = false,
                    volume = volume,
                    memory = memory,
                    battery = battery,
                    device = device,
                    healthScore = computeHealthScore(volume, memory, battery),
                    networkPrivacy = network,
                    activeModeId = activeMode,
                )
            }
            _state.value = next
        }
    }

    private fun computeHealthScore(
        volume: VolumeInfo?,
        memory: MemoryInfo?,
        battery: BatteryInfo?,
    ): Int {
        // Lower usage and cooler battery score higher; simple transparent heuristic.
        // Missing readings contribute their neutral midpoint instead of crashing.
        val storageScore = (1f - (volume?.usedFraction ?: 0.5f)) * 50f
        val ramScore = (1f - (memory?.usedFraction ?: 0.5f)) * 30f
        val tempPenalty = (((battery?.temperatureCelsius ?: 35f) - 35f).coerceAtLeast(0f)) * 1.5f
        return (storageScore + ramScore + 20f - tempPenalty).coerceIn(0f, 100f).toInt()
    }
}
