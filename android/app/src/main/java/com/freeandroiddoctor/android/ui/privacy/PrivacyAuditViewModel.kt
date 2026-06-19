package com.freeandroiddoctor.android.ui.privacy

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.privacy.DeviceRiskReport
import com.freeandroiddoctor.android.engine.privacy.NetworkPrivacyReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PrivacyAuditState(
    val report: DeviceRiskReport? = null,
    val network: NetworkPrivacyReport? = null,
    val running: Boolean = false,
    val includeSystem: Boolean = false,
)

class PrivacyAuditViewModel(app: Application) : AndroidViewModel(app) {

    private val scanner = ServiceLocator.apkStaticScannerEngine
    private val network = ServiceLocator.networkPrivacyEngine

    private val _state = MutableStateFlow(PrivacyAuditState())
    val state: StateFlow<PrivacyAuditState> = _state.asStateFlow()

    init {
        refreshNetwork()
    }

    fun setIncludeSystem(value: Boolean) {
        _state.value = _state.value.copy(includeSystem = value)
    }

    fun refreshNetwork() {
        viewModelScope.launch {
            val snapshot = network.snapshot()
            _state.value = _state.value.copy(network = snapshot)
        }
    }

    fun runAudit() {
        if (_state.value.running) return
        _state.value = _state.value.copy(running = true)
        viewModelScope.launch {
            val report = scanner.scan(includeSystem = _state.value.includeSystem)
            _state.value = _state.value.copy(report = report, running = false)
        }
    }
}
