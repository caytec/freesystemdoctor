package com.freeandroiddoctor.android.ui.insights

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.apps.InsightsReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class InsightsUiState(
    val report: InsightsReport? = null,
    val loading: Boolean = true,
    val needsUsageAccess: Boolean = false,
)

class AppInsightsViewModel : ViewModel() {

    private val engine = ServiceLocator.appInsightsEngine
    private val permissions = ServiceLocator.permissionManager

    private val _state = MutableStateFlow(InsightsUiState())
    val state: StateFlow<InsightsUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, needsUsageAccess = !permissions.hasUsageAccess())
            val report = engine.report()
            _state.value = InsightsUiState(
                report = report,
                loading = false,
                needsUsageAccess = !permissions.hasUsageAccess(),
            )
        }
    }

    fun usageAccessIntent() = permissions.usageAccessSettingsIntent()
}
