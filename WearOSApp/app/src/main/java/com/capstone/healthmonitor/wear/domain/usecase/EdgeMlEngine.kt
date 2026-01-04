package com.capstone.healthmonitor.wear.domain.usecase

import android.content.Context
import android.content.res.AssetFileDescriptor
import android.util.Log
import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import dagger.hilt.android.qualifiers.ApplicationContext
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.abs

/**
 * Edge ML engine that wraps TFLite activity classification and LSTM anomaly detection.
 * Falls back to lightweight heuristic rules when TFLite models are unavailable.
 */
@Singleton
class EdgeMlEngine @Inject constructor(
    @ApplicationContext private val context: Context,
    private val ruleDetector: LocalAnomalyDetector
) {
    companion object {
        private const val TAG = "EdgeMlEngine"
        private const val ACTIVITY_MODEL_ASSET = "models/activity_classifier.tflite"
        private const val ANOMALY_MODEL_ASSET = "models/anomaly_lstm.tflite"
        private const val DEFAULT_MODEL_VERSION = "edge-tflite-v1"
    }

    private val activityLabels = listOf("sleep", "rest", "walk", "run", "exercise", "other")

    private val activityInterpreter: Interpreter? = buildInterpreter(ACTIVITY_MODEL_ASSET)
    private val anomalyInterpreter: Interpreter? = buildInterpreter(ANOMALY_MODEL_ASSET)

    data class ActivityResult(
        val state: String,
        val confidence: Float,
        val modelVersion: String = DEFAULT_MODEL_VERSION,
        val usedTflite: Boolean
    )

    data class AnomalyResult(
        val isAnomaly: Boolean,
        val score: Float,
        val modelVersion: String = DEFAULT_MODEL_VERSION,
        val usedTflite: Boolean
    )

    fun classifyActivity(metric: HealthMetric): ActivityResult {
        val hr = metric.heartRate ?: 0f
        val steps = metric.steps?.toFloat() ?: 0f
        val calories = metric.calories ?: 0f
        val distance = metric.distance ?: 0f

        activityInterpreter?.let { interpreter ->
            return try {
                val input = floatArrayOf(hr, steps, calories, distance)
                val inputTensor = arrayOf(input)
                val output = Array(1) { FloatArray(activityLabels.size) }
                interpreter.run(inputTensor, output)
                val probs = output.first()
                val maxIdx = probs.indices.maxByOrNull { probs[it] } ?: 0
                ActivityResult(
                    state = activityLabels[maxIdx],
                    confidence = probs[maxIdx].coerceIn(0f, 1f),
                    usedTflite = true
                )
            } catch (t: Throwable) {
                Log.w(TAG, "Activity TFLite inference failed, using heuristic", t)
                heuristicActivity(hr, steps)
            }
        }

        return heuristicActivity(hr, steps)
    }

    fun detectAnomaly(metric: HealthMetric, recent: List<HealthMetric>): AnomalyResult {
        val hr = metric.heartRate ?: return AnomalyResult(false, 0f, usedTflite = false)
        val steps = metric.steps?.toFloat() ?: 0f
        val calories = metric.calories ?: 0f
        val distance = metric.distance ?: 0f

        anomalyInterpreter?.let { interpreter ->
            return try {
                // Model expects [1, seq_len, 4] - sequence of (hr, steps, calories, distance)
                // Build sequence from recent metrics + current metric
                val sequence = (recent.takeLast(9) + listOf(metric)).map { m ->
                    floatArrayOf(
                        m.heartRate ?: 0f,
                        m.steps?.toFloat() ?: 0f,
                        m.calories ?: 0f,
                        m.distance ?: 0f
                    )
                }
                // Pad if we don't have 10 samples yet
                val paddedSeq = if (sequence.size < 10) {
                    val padding = List(10 - sequence.size) { floatArrayOf(hr, steps, calories, distance) }
                    padding + sequence
                } else {
                    sequence
                }
                
                val inputTensor = Array(1) { paddedSeq.toTypedArray() }
                val output = Array(1) { Array(10) { FloatArray(4) } }
                interpreter.run(inputTensor, output)
                
                // Compute reconstruction error (MSE) for the last timestep
                val reconstructed = output[0][9]  // Last timestep reconstruction
                val original = floatArrayOf(hr, steps, calories, distance)
                val mse = reconstructed.zip(original).map { (r, o) -> 
                    val diff = r - o
                    diff * diff 
                }.average().toFloat()
                
                // Normalize MSE to 0-1 score (higher MSE = more anomalous)
                // Typical MSE for normal samples is ~20-30, anomalies are 50+
                val score = (mse / 100f).coerceIn(0f, 1f)
                
                AnomalyResult(
                    isAnomaly = score >= 0.5f,
                    score = score,
                    usedTflite = true
                )
            } catch (t: Throwable) {
                Log.w(TAG, "Anomaly TFLite inference failed, using rule fallback", t)
                ruleFallback(metric, recent)
            }
        }

        return ruleFallback(metric, recent)
    }

    private fun ruleFallback(metric: HealthMetric, recent: List<HealthMetric>): AnomalyResult {
        val isSuspicious = ruleDetector.isSuspicious(metric, recent)
        val score = ruleDetector.getLocalScore(metric, recent)
        return AnomalyResult(isSuspicious, score, modelVersion = "rule-fallback", usedTflite = false)
    }

    private fun heuristicActivity(hr: Float, steps: Float): ActivityResult {
        val state = when {
            hr < 50f -> "sleep"
            steps < 20f && hr < 80f -> "rest"
            steps in 20f..200f -> "walk"
            steps > 200f || hr > 130f -> "run"
            else -> "other"
        }
        val confidence = when (state) {
            "sleep" -> 0.7f
            "rest" -> 0.6f
            "walk" -> 0.65f
            "run" -> 0.7f
            else -> 0.5f
        }
        return ActivityResult(state, confidence, modelVersion = "heuristic", usedTflite = false)
    }

    private fun buildInterpreter(assetPath: String): Interpreter? {
        return try {
            val buffer = loadModelFile(assetPath)
            Interpreter(buffer)
        } catch (t: Throwable) {
            Log.w(TAG, "TFLite model not available for $assetPath, falling back", t)
            null
        }
    }

    private fun loadModelFile(assetPath: String): MappedByteBuffer {
        val afd: AssetFileDescriptor = context.assets.openFd(assetPath)
        FileInputStream(afd.fileDescriptor).use { fis ->
            val channel = fis.channel
            val startOffset = afd.startOffset
            val declaredLength = afd.declaredLength
            return channel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
        }
    }
}
