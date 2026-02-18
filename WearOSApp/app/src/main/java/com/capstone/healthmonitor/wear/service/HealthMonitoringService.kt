package com.capstone.healthmonitor.wear.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.concurrent.futures.await
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
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
import kotlinx.coroutines.runBlocking
import javax.inject.Inject

/**
 * Foreground service that continuously monitors health metrics using Health Services API
 */
@AndroidEntryPoint
class HealthMonitoringService : LifecycleService() {

    @Inject
    lateinit var repository: HealthRepository

    private val measureClient by lazy { HealthServices.getClient(this).measureClient }

    // Job for the periodic saving task
    private var savingJob: Job? = null

    // FIX 1 & 2: Use Double for heart rate/calories and Long for steps — these are
    // the native types returned by the Health Services API. We cast to Float/Int
    // only at the saveMetric() call site to match the HealthMetric model.
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

    private val heartRateCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Heart rate availability: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            data.getData(DataType.HEART_RATE_BPM).forEach { dataPoint ->
                val heartRate = dataPoint.value // Double
                if (heartRate > 0.0) {
                    currentHeartRate = heartRate
                    Log.d(TAG, "Heart Rate updated to: $heartRate BPM")
                }
            }
        }
    }

    private val stepsCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Steps availability: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            data.getData(DataType.STEPS).forEach { dataPoint ->
                cumulativeSteps = (cumulativeSteps ?: 0L) + dataPoint.value // Long
                Log.d(TAG, "Steps updated to: $cumulativeSteps")
            }
        }
    }

    private val caloriesCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Calories availability: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            data.getData(DataType.CALORIES).forEach { dataPoint ->
                cumulativeCalories = (cumulativeCalories ?: 0.0) + dataPoint.value // Double
                Log.d(TAG, "Calories updated to: $cumulativeCalories")
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
                Log.d(TAG, "Registering health monitoring callbacks")
                measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, heartRateCallback)
                measureClient.registerMeasureCallback(DataType.STEPS, stepsCallback)
                measureClient.registerMeasureCallback(DataType.CALORIES, caloriesCallback)
                Log.d(TAG, "Health monitoring started for HR, Steps, and Calories")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start health monitoring", e)
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

        // Unregister without blocking the main thread during destruction
        measureClient.unregisterMeasureCallbackAsync(DataType.HEART_RATE_BPM, heartRateCallback)
        measureClient.unregisterMeasureCallbackAsync(DataType.STEPS, stepsCallback)
        measureClient.unregisterMeasureCallbackAsync(DataType.CALORIES, caloriesCallback)

        super.onDestroy()
    }
}