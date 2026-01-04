package com.capstone.healthmonitor.wear.data.repository

import android.util.Log
import com.capstone.healthmonitor.wear.data.local.HealthMetricDao
import com.capstone.healthmonitor.wear.data.network.HealthApiService
import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import com.capstone.healthmonitor.wear.domain.model.HealthMetricRequest
import com.capstone.healthmonitor.wear.domain.usecase.EdgeMlEngine
import com.capstone.healthmonitor.wear.domain.usecase.LocalAnomalyDetector
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class HealthRepository @Inject constructor(
    private val healthMetricDao: HealthMetricDao,
    private val apiService: HealthApiService,
    private val anomalyDetector: LocalAnomalyDetector,
    private val edgeMlEngine: EdgeMlEngine
) {
    companion object {
        private const val TAG = "HealthRepository"
    }

    /**
     * Save health metric to local database
     */
    suspend fun saveMetric(metric: HealthMetric): Result<Long> {
        return try {
            val id = healthMetricDao.insertMetric(metric)
            Result.success(id)
        } catch (e: Exception) {
            Log.e(TAG, "Error saving metric", e)
            Result.failure(e)
        }
    }

    /**
     * Get recent metrics as Flow for UI observation
     */
    fun getRecentMetrics(limit: Int = 50): Flow<List<HealthMetric>> {
        return healthMetricDao.getRecentMetrics(limit)
    }

    /**
     * Get latest metrics as Flow for UI observation (alias for getRecentMetrics)
     */
    fun getLatestMetrics(limit: Int = 10): Flow<List<HealthMetric>> {
        return healthMetricDao.getRecentMetrics(limit)
    }

    /**
     * Get unsynced metrics for cloud synchronization
     */
    suspend fun getUnsyncedMetrics(limit: Int = 100): List<HealthMetric> {
        return healthMetricDao.getUnsyncedMetrics(limit)
    }

    /**
     * Sync metrics to cloud backend with local anomaly flagging
     */
    suspend fun syncMetricsToCloud(): Result<Int> {
        return try {
            val unsyncedMetrics = healthMetricDao.getUnsyncedMetrics(100)
            
            if (unsyncedMetrics.isEmpty()) {
                return Result.success(0)
            }

            // Fetch recent metrics for delta/context checks (non-flow version)
            val recentMetricsForContext = healthMetricDao.getRecentMetricsSync(10)

            // Convert to API request format with local anomaly flagging
            val requests = unsyncedMetrics.map { metric ->
                val activityResult = edgeMlEngine.classifyActivity(metric)
                val anomalyResult = edgeMlEngine.detectAnomaly(metric, recentMetricsForContext)

                val ruleScore = anomalyDetector.getLocalScore(metric, recentMetricsForContext)

                HealthMetricRequest(
                    userId = metric.userId,
                    timestamp = metric.timestamp,
                    metrics = buildMap {
                        metric.heartRate?.let { put("heartRate", it) }
                        metric.steps?.let { put("steps", it) }
                        metric.calories?.let { put("calories", it) }
                        metric.distance?.let { put("distance", it) }
                        metric.batteryLevel?.let { put("batteryLevel", it) }
                        put("activityState", activityResult.state)
                    },
                    deviceId = metric.deviceId,
                    isAnomalous = anomalyResult.isAnomaly,
                    localAnomalyScore = ruleScore,
                    edgeAnomalyScore = anomalyResult.score,
                    activityState = activityResult.state,
                    modelVersion = anomalyResult.modelVersion
                )
            }

            // Send to cloud
            val response = apiService.syncHealthData(requests)

            if (response.isSuccessful && response.body()?.success == true) {
                // Mark as synced
                val ids = unsyncedMetrics.map { it.id }
                healthMetricDao.markAsSynced(ids)
                
                Log.d(TAG, "Successfully synced ${ids.size} metrics")
                Result.success(ids.size)
            } else {
                val error = "Sync failed: ${response.code()} - ${response.message()}"
                Log.e(TAG, error)
                Result.failure(Exception(error))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error syncing metrics", e)
            Result.failure(e)
        }
    }

    /**
     * Clean up old synced data to save storage
     */
    suspend fun cleanupOldData(olderThanDays: Int = 7) {
        val cutoffTimestamp = System.currentTimeMillis() - (olderThanDays * 24 * 60 * 60 * 1000L)
        healthMetricDao.deleteOldSyncedMetrics(cutoffTimestamp)
    }

    /**
     * Get count of unsynced metrics
     */
    suspend fun getUnsyncedCount(): Int {
        return healthMetricDao.getUnsyncedCount()
    }
}
