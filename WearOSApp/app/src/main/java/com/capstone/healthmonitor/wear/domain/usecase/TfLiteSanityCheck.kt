package com.capstone.healthmonitor.wear.domain.usecase

import android.content.Context
import android.util.Log
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Sanity check for TFLite models loaded from assets.
 * Loads both activity classifier and anomaly LSTM models, runs sample inputs, and logs results.
 */
@Singleton
class TfLiteSanityCheck @Inject constructor(
    @ApplicationContext private val context: Context,
    private val edgeMlEngine: EdgeMlEngine
) {
    companion object {
        private const val TAG = "TfLiteSanityCheck"
    }

    fun runChecks() {
        Log.d(TAG, "Starting TFLite sanity checks...")

        // Test activity classifier
        val activityTestMetric = com.capstone.healthmonitor.wear.domain.model.HealthMetric(
            id = 1L,
            userId = "sanity-check-user",
            timestamp = System.currentTimeMillis(),
            heartRate = 75f,     // near walk/moderate activity
            steps = 120,
            calories = 35f,
            distance = 0.4f,
            deviceId = "sanity-check-device"
        )
        val activityResult = edgeMlEngine.classifyActivity(activityTestMetric)
        Log.d(TAG, "Activity Classifier Sanity Check:")
        Log.d(TAG, "  Input: HR=75, Steps=120, Calories=35, Distance=0.4")
        Log.d(TAG, "  Output: state=${activityResult.state}, confidence=${activityResult.confidence}, usedTflite=${activityResult.usedTflite}")
        Log.d(TAG, "  Model Version: ${activityResult.modelVersion}")

        // Test anomaly detector with normal-like sample
        val anomalyTestMetric = com.capstone.healthmonitor.wear.domain.model.HealthMetric(
            id = 2L,
            userId = "sanity-check-user",
            timestamp = System.currentTimeMillis(),
            heartRate = 80f,
            steps = 100,
            calories = 30f,
            distance = 0.3f,
            deviceId = "sanity-check-device"
        )
        val recentMetrics = listOf(
            anomalyTestMetric.copy(id = 2L, heartRate = 78f, steps = 95),
            anomalyTestMetric.copy(id = 3L, heartRate = 82f, steps = 105)
        )
        val anomalyResult = edgeMlEngine.detectAnomaly(anomalyTestMetric, recentMetrics)
        Log.d(TAG, "Anomaly Detector Sanity Check:")
        Log.d(TAG, "  Input: HR=80, Steps=100, Calories=30, Distance=0.3")
        Log.d(TAG, "  Output: isAnomaly=${anomalyResult.isAnomaly}, score=${anomalyResult.score}, usedTflite=${anomalyResult.usedTflite}")
        Log.d(TAG, "  Model Version: ${anomalyResult.modelVersion}")

        // Test anomaly detector with anomalous sample
        val anomalousMetric = anomalyTestMetric.copy(
            id = 4L,
            heartRate = 160f,  // very high HR
            steps = 20,        // low steps
            calories = 10f
        )
        val anomalousResult = edgeMlEngine.detectAnomaly(anomalousMetric, recentMetrics)
        Log.d(TAG, "Anomaly Detector High-Risk Sample:")
        Log.d(TAG, "  Input: HR=160, Steps=20, Calories=10, Distance=0.3")
        Log.d(TAG, "  Output: isAnomaly=${anomalousResult.isAnomaly}, score=${anomalousResult.score}, usedTflite=${anomalousResult.usedTflite}")

        Log.d(TAG, "TFLite sanity checks complete!")
    }
}
