package com.freesystemdoctor.android.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.battery.BatteryInfo
import com.freesystemdoctor.android.engine.device.DeviceInfo
import com.freesystemdoctor.android.engine.memory.MemoryInfo
import com.freesystemdoctor.android.engine.privacy.NetworkPrivacyReport
import com.freesystemdoctor.android.engine.storage.VolumeInfo
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
            val volume = withContext(Dispatchers.IO) { ServiceLocator.storageEngine.readPrimaryVolume() }
            val memory = ServiceLocator.memoryEngine.read()
            val battery = ServiceLocator.batteryEngine.read()
            val device = ServiceLocator.deviceInfoEngine.read()
            val network = runCatching { ServiceLocator.networkPrivacyEngine.snapshot() }.getOrNull()
            val activeMode = runCatching { ServiceLocator.modeStore.activeSnapshotOnce()?.activeModeId }.getOrNull()
            _state.value = DashboardUiState(
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
    }

    private fun computeHealthScore(
        volume: VolumeInfo,
        memory: MemoryInfo,
        battery: BatteryInfo,
    ): Int {
        // Lower usage and cooler battery score higher; simple transparent heuristic.
        val storageScore = (1f - volume.usedFraction) * 50f
        val ramScore = (1f - memory.usedFraction) * 30f
        val tempPenalty = ((battery.temperatureCelsius - 35f).coerceAtLeast(0f)) * 1.5f
        return (storageScore + ramScore + 20f - tempPenalty).coerceIn(0f, 100f).toInt()
    }
}
