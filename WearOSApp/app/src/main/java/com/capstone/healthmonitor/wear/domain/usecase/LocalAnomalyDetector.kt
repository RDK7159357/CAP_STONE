package com.capstone.healthmonitor.wear.domain.usecase

import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Lightweight on-device anomaly detection using simple rules.
 * Flags suspicious metrics for cloud verification via LSTM.
 * Returns human-readable reasons explaining why each anomaly was flagged.
 */
@Singleton
class LocalAnomalyDetector @Inject constructor() {

    companion object {
        private const val HR_THRESHOLD_HIGH = 140f // BPM
        private const val HR_THRESHOLD_LOW = 40f    // BPM
        private const val HR_DELTA_THRESHOLD = 30f  // BPM jump in one sample
    }

    /**
     * Check if a metric should be flagged for cloud anomaly scoring.
     * Returns true if any simple rule is violated.
     */
    fun isSuspicious(metric: HealthMetric, recentMetrics: List<HealthMetric> = emptyList()): Boolean {
        return getAnomalyReasons(metric, recentMetrics).isNotEmpty()
    }

    /**
     * Get human-readable reasons why this metric was flagged as anomalous.
     * Returns an empty list if the metric appears normal.
     */
    fun getAnomalyReasons(metric: HealthMetric, recentMetrics: List<HealthMetric> = emptyList()): List<String> {
        val hr = metric.heartRate ?: return emptyList()
        val reasons = mutableListOf<String>()

        // Rule 1: Absolute threshold
        when {
            hr >= 170f -> reasons.add("Heart rate ${hr.toInt()} BPM is dangerously high (threshold: ${HR_THRESHOLD_HIGH.toInt()} BPM)")
            hr >= HR_THRESHOLD_HIGH -> reasons.add("Heart rate ${hr.toInt()} BPM exceeds safe threshold (${HR_THRESHOLD_HIGH.toInt()} BPM)")
            hr <= HR_THRESHOLD_LOW -> reasons.add("Heart rate ${hr.toInt()} BPM is critically low (threshold: ${HR_THRESHOLD_LOW.toInt()} BPM)")
        }

        // Rule 2: Sudden spike/drop from previous sample
        if (recentMetrics.isNotEmpty()) {
            val previousHr = recentMetrics.firstOrNull()?.heartRate
            if (previousHr != null) {
                val delta = kotlin.math.abs(hr - previousHr)
                if (delta >= HR_DELTA_THRESHOLD) {
                    val direction = if (hr > previousHr) "spike" else "drop"
                    reasons.add(
                        "Sudden heart rate $direction: ${previousHr.toInt()} → ${hr.toInt()} BPM " +
                        "(${delta.toInt()} BPM change in one reading)"
                    )
                }
            }
        }

        return reasons
    }

    /**
     * Get a simple anomaly score (0–1) based on local rules.
     * 0 = normal, 1 = highly suspicious.
     * Cloud score should override this.
     */
    fun getLocalScore(metric: HealthMetric, recentMetrics: List<HealthMetric> = emptyList()): Float {
        val hr = metric.heartRate ?: return 0f

        val thresholdScore = when {
            hr >= 170f -> 1f
            hr >= 150f -> 0.8f
            hr >= 140f -> 0.6f
            hr <= 40f -> 0.7f
            hr <= 50f -> 0.4f
            else -> 0f
        }

        val deltaScore = if (recentMetrics.isNotEmpty()) {
            val previousHr = recentMetrics.firstOrNull()?.heartRate ?: return thresholdScore
            val delta = kotlin.math.abs(hr - previousHr)
            when {
                delta >= 50f -> 0.8f
                delta >= 30f -> 0.5f
                else -> 0f
            }
        } else {
            0f
        }

        return maxOf(thresholdScore, deltaScore)
    }
}
