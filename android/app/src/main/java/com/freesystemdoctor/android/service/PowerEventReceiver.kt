package com.freesystemdoctor.android.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Starts/stops [ChargingSessionService] on power-plug events. */
class PowerEventReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            Intent.ACTION_POWER_CONNECTED -> ChargingSessionService.start(context.applicationContext)
            Intent.ACTION_POWER_DISCONNECTED -> ChargingSessionService.stop(context.applicationContext)
        }
    }
}
