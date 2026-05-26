package com.freesystemdoctor.android.ui.battery

import androidx.lifecycle.ViewModel
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.battery.BatteryInfo

class BatteryViewModel : ViewModel() {

    private val engine = ServiceLocator.batteryEngine
    private val tweaks = ServiceLocator.systemTweaksEngine

    fun read(): BatteryInfo = engine.read()
    fun isIgnoringOptimization() = tweaks.isIgnoringBatteryOptimizations()
    fun ignoreBatteryIntent() = tweaks.ignoreBatteryOptimizationsIntent()
}
