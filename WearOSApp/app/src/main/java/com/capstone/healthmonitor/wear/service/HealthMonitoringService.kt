package com.capstone.healthmonitor.wear.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.concurrent.futures.await
import androidx.health.services.client.HealthServices
import androidx.health.services.client.PassiveListenerCallback
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.PassiveMonitoringCapabilities
import androidx.health.services.client.data.PassiveMonitoringConfig
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import com.capstone.healthmonitor.wear.data.repository.HealthRepository
import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Foreground service that continuously monitors health metrics using Health Services API
 * Uses PassiveMonitoringClient for continuous background data collection
 */
@AndroidEntryPoint
class HealthMonitoringService : LifecycleService() {

    @Inject
    lateinit var repository: HealthRepository

    private val passiveMonitoringClient by lazy { 
        HealthServices.getClient(this).passiveMonitoringClient 
    }

    // Job for the periodic saving task
    private var savingJob: Job? = null

    @Volatile private var currentHeartRate: Double? = null
    @Volatile private var cumulativeSteps: Long? = null
    @Volatile private var cumulativeCalories: Double? = null

    companion object {
        private const val TAG = "HealthMonitorService"
        private const val NOTIFICATION_ID = 1
        private const val CHANNEL_ID = "health_monitor_channel"
        private const val CHANNEL_NAME = "Health Monitoring"
        private const val SAVE_INTERVAL_MS = 30_000L // 30 seconds

        // User ID - In production, get from authentication
        private const val USER_ID = "user_001"

        // Device ID - In production, get unique device identifier
        private val DEVICE_ID = "wear_${android.os.Build.MODEL}"
    }

    private val passiveListenerCallback = object : PassiveListenerCallback {
        override fun onNewDataPointsReceived(dataPoints: DataPointContainer) {
            dataPoints.getData(DataType.HEART_RATE_BPM).forEach { dataPoint ->
                val heartRate = dataPoint.value
                if (heartRate > 0.0) {
                    currentHeartRate = heartRate
                    Log.d(TAG, "Background Heart Rate: $heartRate BPM")
                }
            }

            dataPoints.getData(DataType.STEPS).forEach { dataPoint ->
                cumulativeSteps = (cumulativeSteps ?: 0L) + dataPoint.value
                Log.d(TAG, "Background Steps: $cumulativeSteps")
            }

            dataPoints.getData(DataType.CALORIES).forEach { dataPoint ->
                cumulativeCalories = (cumulativeCalories ?: 0.0) + dataPoint.value
                Log.d(TAG, "Background Calories: $cumulativeCalories")
            }
        }
    }

    // In HealthMonitoringService.kt
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()

        // Explicitly define the service type to match the manifest
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                createNotification(),
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH
            )
        } else {
            startForeground(NOTIFICATION_ID, createNotification())
        }

        startHealthMonitoring()
        startPeriodicSaving()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        return START_STICKY
    }

    override fun onBind(intent: Intent): IBinder? {
        super.onBind(intent)
        return null
    }

    private fun startHealthMonitoring() {
        lifecycleScope.launch {
            try {
                Log.d(TAG, "Checking passive monitoring capabilities...")
                
                // Check if the device supports passive monitoring
                val capabilities = passiveMonitoringClient.getCapabilitiesAsync().await()
                Log.d(TAG, "Passive monitoring supported data types: ${capabilities.supportedDataTypesPassiveMonitoring}")
                
                // Configure passive monitoring for continuous background data collection
                val passiveMonitoringConfig = PassiveMonitoringConfig.builder()
                    .setDataTypes(
                        setOf(
                            DataType.HEART_RATE_BPM,
                            DataType.STEPS,
                            DataType.CALORIES
                        )
                    )
                    .build()

                Log.d(TAG, "Setting up passive listener callback...")
                passiveMonitoringClient.setPassiveListenerCallback(
                    passiveMonitoringConfig,
                    passiveListenerCallback
                )
                
                Log.d(TAG, "Passive health monitoring started successfully for continuous background tracking")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start passive health monitoring", e)
            }
        }
    }

    private fun startPeriodicSaving() {
        savingJob?.cancel()
        savingJob = lifecycleScope.launch(Dispatchers.IO) {
            while (isActive) {
                delay(SAVE_INTERVAL_MS)
                saveMetricToDatabase()
            }
        }
        Log.d(TAG, "Periodic saving started every $SAVE_INTERVAL_MS ms")
    }

    private fun saveMetricToDatabase() {
        val heartRateToSave = currentHeartRate

        // STRICTER CHECK: Ensure we don't save a 0.0 heart rate
        if (heartRateToSave == null || heartRateToSave <= 0.0) {
            return
        }

        lifecycleScope.launch(Dispatchers.IO) {
            val metric = HealthMetric(
                userId = USER_ID,
                timestamp = System.currentTimeMillis(),
                heartRate = heartRateToSave.toFloat(),
                steps = cumulativeSteps?.toInt() ?: 0, // Ensure a default here
                calories = cumulativeCalories?.toFloat() ?: 0f, // Ensure a default here
                deviceId = DEVICE_ID,
                batteryLevel = getBatteryLevel(),
                isSynced = false
            )
            repository.saveMetric(metric)
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
        // Cancel the saving loop immediately
        savingJob?.cancel()

        // Clear passive listener callback to stop background monitoring
        lifecycleScope.launch {
            try {
                passiveMonitoringClient.clearPassiveListenerCallbackAsync().await()
                Log.d(TAG, "Passive monitoring stopped")
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping passive monitoring", e)
            }
        }

        super.onDestroy()
    }
}