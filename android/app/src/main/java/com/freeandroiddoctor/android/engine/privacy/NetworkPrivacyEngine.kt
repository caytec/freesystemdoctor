package com.freeandroiddoctor.android.engine.privacy

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.wifi.WifiManager
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

enum class PrivacyDot { GOOD, WARN, BAD, UNKNOWN }

data class NetworkPrivacyReport(
    val vpnActive: PrivacyDot,
    val privateDns: PrivacyDot,
    val wifiSecurity: PrivacyDot,
    val captivePortal: PrivacyDot,
    val ipv6: PrivacyDot,
    val privateDnsHost: String? = null,
    val wifiSsid: String? = null,
) {
    val score: Int
        get() {
            val weights = listOf(vpnActive, privateDns, wifiSecurity, captivePortal, ipv6)
                .map { dotPoints(it) }
            val total = weights.sum()
            val max = weights.size * MAX_POINTS
            return (total * 100 / max.coerceAtLeast(1)).coerceIn(0, 100)
        }

    private fun dotPoints(dot: PrivacyDot): Int = when (dot) {
        PrivacyDot.GOOD -> MAX_POINTS
        PrivacyDot.WARN -> MAX_POINTS / 2
        PrivacyDot.BAD -> 0
        PrivacyDot.UNKNOWN -> MAX_POINTS / 2
    }

    companion object {
        private const val MAX_POINTS = 4
    }
}

/**
 * Read-only network-privacy snapshot: does the user have a VPN active, private DNS
 * configured, are they on an unsecured Wi-Fi, etc. Everything derives from
 * [ConnectivityManager] / [WifiManager] — no probes, no DNS lookups.
 */
class NetworkPrivacyEngine(private val context: Context) {

    suspend fun snapshot(): NetworkPrivacyReport = withContext(Dispatchers.Default) {
        val cm = context.getSystemService(ConnectivityManager::class.java)
        val active = cm?.activeNetwork
        val caps = active?.let { runCatching { cm.getNetworkCapabilities(it) }.getOrNull() }
        val link = active?.let { runCatching { cm.getLinkProperties(it) }.getOrNull() }

        val vpn = when {
            caps == null -> PrivacyDot.UNKNOWN
            caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN) -> PrivacyDot.GOOD
            else -> PrivacyDot.WARN
        }

        val privateDnsHost = link?.let {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) it.privateDnsServerName else null
        }
        val privateDns = when {
            link == null -> PrivacyDot.UNKNOWN
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.P && link.isPrivateDnsActive -> PrivacyDot.GOOD
            else -> PrivacyDot.WARN
        }

        val captive = when {
            caps == null -> PrivacyDot.UNKNOWN
            caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL) -> PrivacyDot.BAD
            else -> PrivacyDot.GOOD
        }

        val ipv6 = when {
            link == null -> PrivacyDot.UNKNOWN
            link.linkAddresses.any { it.address.hostAddress?.contains(":") == true } -> PrivacyDot.GOOD
            else -> PrivacyDot.WARN
        }

        val (wifiSecurity, wifiSsid) = wifiSecurityAndSsid(caps)

        NetworkPrivacyReport(
            vpnActive = vpn,
            privateDns = privateDns,
            wifiSecurity = wifiSecurity,
            captivePortal = captive,
            ipv6 = ipv6,
            privateDnsHost = privateDnsHost,
            wifiSsid = wifiSsid,
        )
    }

    @Suppress("DEPRECATION")
    private fun wifiSecurityAndSsid(caps: NetworkCapabilities?): Pair<PrivacyDot, String?> {
        if (caps == null || !caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
            return PrivacyDot.UNKNOWN to null
        }
        val wifi = runCatching { context.getSystemService(WifiManager::class.java) }.getOrNull()
            ?: return PrivacyDot.UNKNOWN to null
        val info = runCatching { wifi.connectionInfo }.getOrNull() ?: return PrivacyDot.UNKNOWN to null

        val ssid = info.ssid?.trim('"')?.takeIf { it.isNotBlank() && it != "<unknown ssid>" }
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            // WifiInfo.SECURITY_TYPE_OPEN=0, WEP=1 → bad; PSK/EAP/SAE/OWE=2+ → good.
            val type = runCatching { info.currentSecurityType }.getOrNull()
                ?: return PrivacyDot.WARN to ssid
            val dot = when {
                type <= 1 -> PrivacyDot.BAD
                else -> PrivacyDot.GOOD
            }
            dot to ssid
        } else {
            PrivacyDot.WARN to ssid
        }
    }
}
