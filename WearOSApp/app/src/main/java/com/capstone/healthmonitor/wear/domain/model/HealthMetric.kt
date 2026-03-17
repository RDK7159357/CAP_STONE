package com.capstone.healthmonitor.wear.domain.model
import androidx.room.Entity
import androidx.room.Ignore
import androidx.room.PrimaryKey

@Entity(tableName = "health_metrics")
data class HealthMetric(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val userId: String,
    val timestamp: Long,
    val heartRate: Float? = null,
    val steps: Int? = null,
    val calories: Float? = null,
    val distance: Float? = null,
    val isSynced: Boolean = false,
    val deviceId: String,
    val batteryLevel: Int? = null
) {
    @Ignore
    var anomalyReasons: List<String> = emptyList()
}

data class HealthMetricRequest(
    val userId: String,
    val timestamp: Long,
    val metrics: Map<String, Any>,
    val deviceId: String,
    val isAnomalous: Boolean = false,
    val localAnomalyScore: Float = 0f,
    val edgeAnomalyScore: Float? = null,
    val activityState: String? = null,
    val modelVersion: String? = null,
    val anomalyReasons: List<String>? = null
)

data class HealthMetricResponse(
    val success: Boolean,
    val message: String,
    val anomalyDetected: Boolean = false,
    val anomalyScore: Float = 0f,
    val anomalyReasons: List<String>? = null
)
