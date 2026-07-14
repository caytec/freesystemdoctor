package com.freeandroiddoctor.android.engine.battery

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager

data class BatteryInfo(
    val levelPercent: Int,
    val isCharging: Boolean,
    val temperatureCelsius: Float,
    val voltageVolts: Float,
    val technology: String,
    val chargeCounterMah: Int?,
    val currentNowMa: Int?,
    val currentAverageMa: Int?,
)

/**
 * Battery facts that are readable without root. Note: true battery "health" / wear
 * (design vs current mAh) is not reliably exposed without root on most OEMs, so we
 * deliberately do not report it.
 */
class BatteryEngine(private val context: Context) {

    fun read(): BatteryInfo {
        val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val level = intent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = intent?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        val percent = if (level >= 0 && scale > 0) (level * 100) / scale else 0

        val status = intent?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
        val charging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
            status == BatteryManager.BATTERY_STATUS_FULL

        val tempTenths = intent?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0) ?: 0
        val voltageMv = intent?.getIntExtra(BatteryManager.EXTRA_VOLTAGE, 0) ?: 0
        val tech = intent?.getStringExtra(BatteryManager.EXTRA_TECHNOLOGY).orEmpty()

        val bm = context.getSystemService(Context.BATTERY_SERVICE) as? BatteryManager
        val counter = bm?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CHARGE_COUNTER)
        val counterMah = counter?.takeIf { it > 0 }?.let { it / 1000 }
        val currentNow = bm?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_NOW)
            ?.takeIf { it != Int.MIN_VALUE && it != 0 }?.let { it / 1000 }
        val currentAvg = bm?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_AVERAGE)
            ?.takeIf { it != Int.MIN_VALUE && it != 0 }?.let { it / 1000 }

        return BatteryInfo(
            levelPercent = percent,
            isCharging = charging,
            temperatureCelsius = tempTenths / 10f,
            voltageVolts = voltageMv / 1000f,
            technology = tech,
            chargeCounterMah = counterMah,
            currentNowMa = currentNow,
            currentAverageMa = currentAvg,
        )
    }

    /** Lightweight level + charging snapshot for the alarm worker. */
    fun snapshot(): Pair<Int, Boolean> {
        val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            ?: return 0 to false
        val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        val pct = if (level >= 0 && scale > 0) (level * 100) / scale else 0
        val status = intent.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
        val charging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
            status == BatteryManager.BATTERY_STATUS_FULL
        return pct to charging
    }
}
