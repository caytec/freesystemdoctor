package com.freesystemdoctor.android.engine.network

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.wifi.WifiManager
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class WifiNetwork(
    val ssid: String,
    val signalLevel: Int,
    val frequencyMhz: Int,
    val channel: Int,
    val secured: Boolean,
) {
    val band: String get() = if (frequencyMhz >= 5000) "5 GHz" else "2.4 GHz"
}

/**
 * Lists nearby Wi-Fi access points. Requires ACCESS_FINE_LOCATION (Android ties
 * Wi-Fi scan results to location) plus location services enabled.
 */
class WifiAnalyzerEngine(private val context: Context) {

    fun hasLocationPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED

    @android.annotation.SuppressLint("MissingPermission")
    @Suppress("DEPRECATION")
    suspend fun scan(): List<WifiNetwork> = withContext(Dispatchers.IO) {
        if (!hasLocationPermission()) return@withContext emptyList()
        val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            ?: return@withContext emptyList()
        val results = runCatching { wm.scanResults }.getOrNull().orEmpty()
        results.map { r ->
            WifiNetwork(
                ssid = r.SSID.ifBlank { "<hidden>" },
                signalLevel = WifiManager.calculateSignalLevel(r.level, 5),
                frequencyMhz = r.frequency,
                channel = channelFor(r.frequency),
                secured = r.capabilities.contains("WPA") || r.capabilities.contains("WEP"),
            )
        }.sortedByDescending { it.signalLevel }
    }

    private fun channelFor(freq: Int): Int = when {
        freq == 2484 -> 14
        freq in 2412..2472 -> (freq - 2412) / 5 + 1
        freq in 5170..5825 -> (freq - 5170) / 5 + 34
        else -> 0
    }
}
