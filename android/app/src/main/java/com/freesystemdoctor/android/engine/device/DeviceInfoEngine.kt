package com.freesystemdoctor.android.engine.device

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorManager
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

data class DeviceInfo(
    val manufacturer: String,
    val model: String,
    val androidVersion: String,
    val sdkInt: Int,
    val cpuCores: Int,
    val supportedAbis: List<String>,
)

data class DeviceDetails(
    val manufacturer: String,
    val model: String,
    val device: String,
    val board: String,
    val hardware: String,
    val androidVersion: String,
    val sdkInt: Int,
    val securityPatch: String,
    val kernel: String,
    val cpuCores: Int,
    val cpuMaxFreqMhz: Int?,
    val supportedAbis: List<String>,
    val sensors: List<String>,
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

    suspend fun details(): DeviceDetails = withContext(Dispatchers.IO) {
        val sm = context.getSystemService(Context.SENSOR_SERVICE) as? SensorManager
        val sensors = sm?.getSensorList(Sensor.TYPE_ALL)?.map { it.name }?.distinct().orEmpty()
        DeviceDetails(
            manufacturer = Build.MANUFACTURER.replaceFirstChar { it.uppercase() },
            model = Build.MODEL,
            device = Build.DEVICE,
            board = Build.BOARD,
            hardware = Build.HARDWARE,
            androidVersion = Build.VERSION.RELEASE,
            sdkInt = Build.VERSION.SDK_INT,
            securityPatch = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                Build.VERSION.SECURITY_PATCH
            } else {
                "?"
            },
            kernel = System.getProperty("os.version") ?: "?",
            cpuCores = Runtime.getRuntime().availableProcessors(),
            cpuMaxFreqMhz = readMaxCpuFreqMhz(),
            supportedAbis = Build.SUPPORTED_ABIS.toList(),
            sensors = sensors,
        )
    }

    /** Best-effort: cpufreq sysfs is sometimes world-readable, often not. */
    private fun readMaxCpuFreqMhz(): Int? {
        var maxKhz = 0L
        for (cpu in 0 until Runtime.getRuntime().availableProcessors()) {
            val path = "/sys/devices/system/cpu/cpu$cpu/cpufreq/cpuinfo_max_freq"
            runCatching {
                val value = File(path).readText().trim().toLongOrNull() ?: 0L
                if (value > maxKhz) maxKhz = value
            }
        }
        return if (maxKhz > 0) (maxKhz / 1000).toInt() else null
    }
}
