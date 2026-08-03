package com.freeandroiddoctor.android.ui.phonehome

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.network.PhoneHomeItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PhoneHomeUiState(
    val hasUsageAccess: Boolean = true,
    val loading: Boolean = true,
    val items: List<PhoneHomeItem> = emptyList(),
)

class PhoneHomeViewModel : ViewModel() {

    private val engine = ServiceLocator.dataUsageEngine
    private val permissions = ServiceLocator.permissionManager

    private val _state = MutableStateFlow(PhoneHomeUiState())
    val state: StateFlow<PhoneHomeUiState> = _state.asStateFlow()

    fun load() {
        val hasAccess = permissions.hasUsageAccess()
        _state.value = _state.value.copy(hasUsageAccess = hasAccess, loading = true)
        if (!hasAccess) {
            _state.value = _state.value.copy(loading = false)
            return
        }
        viewModelScope.launch {
            runCatching { engine.backgroundActivity() }
                .onSuccess { _state.value = PhoneHomeUiState(true, false, it) }
                .onFailure { _state.value = _state.value.copy(loading = false) }
        }
    }

    fun usageAccessIntent(): Intent =
        Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    fun appDetailsIntent(pkg: String): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:$pkg")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
}
