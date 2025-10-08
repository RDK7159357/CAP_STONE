package com.capstone.healthmonitor.wear.domain.model

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Data model representing health metrics collected from the watch
 */
@Entity(tableName = "health_metrics")
data class HealthMetric(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    val userId: String,
    
    val timestamp: Long, // Unix timestamp in milliseconds
    
    val heartRate: Float? = null, // BPM
    
    val steps: Int? = null,
    
    val calories: Float? = null, // kcal
    
    val distance: Float? = null, // meters
    
    val isSynced: Boolean = false, // Track sync status
    
    val deviceId: String, // Unique device identifier
    
    val batteryLevel: Int? = null // Battery percentage at time of measurement
)

/**
 * API request model for sending data to cloud
 */
data class HealthMetricRequest(
    val userId: String,
    val timestamp: Long,
    val metrics: Map<String, Any>,
    val deviceId: String
)

/**
 * API response model
 */
data class HealthMetricResponse(
    val success: Boolean,
    val message: String,
    val anomalyDetected: Boolean = false
)
