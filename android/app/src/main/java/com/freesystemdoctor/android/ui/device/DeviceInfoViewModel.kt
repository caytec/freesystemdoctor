package com.freesystemdoctor.android.ui.device

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.device.DeviceDetails
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class DeviceInfoViewModel : ViewModel() {

    private val engine = ServiceLocator.deviceInfoEngine
    private val _details = MutableStateFlow<DeviceDetails?>(null)
    val details: StateFlow<DeviceDetails?> = _details.asStateFlow()

    fun load() {
        if (_details.value != null) return
        viewModelScope.launch { _details.value = engine.details() }
    }
}
