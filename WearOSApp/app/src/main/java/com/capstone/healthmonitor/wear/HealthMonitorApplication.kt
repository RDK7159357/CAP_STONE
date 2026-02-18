package com.capstone.healthmonitor.wear

import android.app.Application
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.content.ContextCompat
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.capstone.healthmonitor.wear.service.HealthMonitoringService
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class HealthMonitorApplication : Application(), Configuration.Provider {

    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()
        
        // Auto-start health monitoring service if permissions are granted
        startHealthMonitoringServiceIfPermitted()
    }

    private fun startHealthMonitoringServiceIfPermitted() {
        val hasBodySensors = ContextCompat.checkSelfPermission(
            this,
            android.Manifest.permission.BODY_SENSORS
        ) == PackageManager.PERMISSION_GRANTED

        val hasActivityRecognition = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.ACTIVITY_RECOGNITION
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }

        if (hasBodySensors && hasActivityRecognition) {
            try {
                val serviceIntent = Intent(this, HealthMonitoringService::class.java)
                ContextCompat.startForegroundService(this, serviceIntent)
                Log.d("HealthMonitorApp", "Health monitoring service auto-started")
            } catch (e: Exception) {
                Log.e("HealthMonitorApp", "Failed to auto-start service", e)
            }
        } else {
            Log.d("HealthMonitorApp", "Permissions not granted, service will start after permission grant")
        }
    }

    override fun getWorkManagerConfiguration(): Configuration {
        return Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
    }
}
