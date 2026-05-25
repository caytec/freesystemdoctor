package com.freesystemdoctor.android.engine.device

import android.content.Context
import android.os.Build

data class DeviceInfo(
    val manufacturer: String,
    val model: String,
    val androidVersion: String,
    val sdkInt: Int,
    val cpuCores: Int,
    val supportedAbis: List<String>,
)

class DeviceInfoEngine(@Suppress("unused") private val context: Context) {

    fun read(): DeviceInfo = DeviceInfo(
        manufacturer = Build.MANUFACTURER.replaceFirstChar { it.uppercase() },
        model = Build.MODEL,
        androidVersion = Build.VERSION.RELEASE,
        sdkInt = Build.VERSION.SDK_INT,
        cpuCores = Runtime.getRuntime().availableProcessors(),
        supportedAbis = Build.SUPPORTED_ABIS.toList(),
    )
}
