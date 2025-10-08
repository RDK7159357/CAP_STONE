package com.capstone.healthmonitor.wear.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import com.capstone.healthmonitor.wear.data.repository.HealthRepository
import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Foreground service that continuously monitors health metrics using Health Services API
 */
@AndroidEntryPoint
class HealthMonitoringService : Service() {

    @Inject
    lateinit var repository: HealthRepository

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val measureClient by lazy { HealthServices.getClient(this).measureClient }
    
    private var currentHeartRate: Float? = null
    private var currentSteps: Int? = null
    private var currentCalories: Float? = null

    companion object {
        private const val TAG = "HealthMonitorService"
        private const val NOTIFICATION_ID = 1
        private const val CHANNEL_ID = "health_monitor_channel"
        private const val CHANNEL_NAME = "Health Monitoring"
        
        // User ID - In production, get from authentication
        private const val USER_ID = "user_001"
        
        // Device ID - In production, get unique device identifier
        private val DEVICE_ID = "wear_${android.os.Build.MODEL}"
    }

    private val heartRateCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(
            dataType: DeltaDataType<*, *>,
            availability: Availability
        ) {
            Log.d(TAG, "Heart rate availability: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            val heartRateData = data.getData(DataType.HEART_RATE_BPM)
            heartRateData.forEach { dataPoint ->
                currentHeartRate = dataPoint.value.toFloat()
                Log.d(TAG, "Heart Rate: ${dataPoint.value} BPM")
                saveMetricToDatabase()
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, createNotification())
        startHealthMonitoring()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startHealthMonitoring() {
        serviceScope.launch {
            try {
                // Register for heart rate updates
                measureClient.registerMeasureCallback(
                    DataType.HEART_RATE_BPM,
                    heartRateCallback
                )
                Log.d(TAG, "Health monitoring started")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start health monitoring", e)
            }
        }
    }

    private fun saveMetricToDatabase() {
        serviceScope.launch(Dispatchers.IO) {
            try {
                val metric = HealthMetric(
                    userId = USER_ID,
                    timestamp = System.currentTimeMillis(),
                    heartRate = currentHeartRate,
                    steps = currentSteps,
                    calories = currentCalories,
                    deviceId = DEVICE_ID,
                    batteryLevel = getBatteryLevel(),
                    isSynced = false
                )

                repository.saveMetric(metric)
                Log.d(TAG, "Metric saved: HR=${currentHeartRate}")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to save metric", e)
            }
        }
    }

    private fun getBatteryLevel(): Int {
        val batteryManager = getSystemService(BATTERY_SERVICE) as android.os.BatteryManager
        return batteryManager.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Health monitoring service notification"
        }

        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.createNotificationChannel(channel)
    }

    private fun createNotification(): Notification {
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("Health Monitor Active")
            .setContentText("Monitoring your vital signs")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
        Log.d(TAG, "Health monitoring service destroyed")
    }
}
