package com.capstone.healthmonitor.wear.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.content.ContextCompat

/**
 * BroadcastReceiver that starts the HealthMonitoringService when the device boots up.
 */
class BootReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "BootReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.d(TAG, "Boot completed, starting HealthMonitoringService")
            val serviceIntent = Intent(context, HealthMonitoringService::class.java)
            ContextCompat.startForegroundService(context, serviceIntent)
        }
    }
}
