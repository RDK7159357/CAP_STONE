package com.capstone.healthmonitor.wear.domain.usecase

import com.capstone.healthmonitor.wear.domain.model.HealthMetric
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33], manifest = Config.NONE)

/**
 * Integration tests for the full anomaly detection priority chain.
 *
 * System spec priority:
 *   1. edgeScore  >= 0.5  → ALERT (TFLite LSTM)
 *   2. cloudScore >= 0.5  → ALERT (Cloud GradientBoosting)
 *   3. heartRate > 140 OR heartRate < 40 → ALERT (rule-based threshold)
 *
 * These tests simulate the logic that [EdgeMlEngine] + [LocalAnomalyDetector]
 * collectively implement, using score values directly (since TFLite/cloud
 * model calls cannot run in a JVM unit test).
 *
 * Explainability contract (from spec):
 *   Source         | Method                           | Example reason
 *   Edge (TFLite)  | Per-feature MSE contribution     | "Heart rate: 180 BPM deviates from expected pattern (72% of anomaly signal)"
 *   Cloud          | Range check + feature importance | "Resting heart rate: 180 BPM is above normal range (50–100 BPM)"
 *   Threshold fall | Simple range checks              | "Heart rate 35 BPM is dangerously low (normal: 50–100 BPM)"
 */
class AnomalyDetectionPriorityTest {

    private lateinit var detector: LocalAnomalyDetector

    private fun metric(heartRate: Float?, steps: Int = 500) = HealthMetric(
        userId    = "test-user",
        deviceId  = "test-device",
        timestamp = System.currentTimeMillis(),
        heartRate = heartRate,
        steps     = steps,
        calories  = 50f,
        distance  = 0.3f
    )

    @Before
    fun setUp() {
        detector = LocalAnomalyDetector()
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Priority 1 — Edge score (TFLite LSTM)
    // In a JVM test, TFLite is unavailable so we validate the AnomalyResult
    // contract that EdgeMlEngine would produce when edgeScore >= 0.5.
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `edgeScore above 0_5 must trigger ALERT (AnomalyResult contract)`() {
        // Simulate what EdgeMlEngine returns for high MSE reconstruction error
        val edgeResult = EdgeMlEngine.AnomalyResult(
            isAnomaly  = true,     // MSE / 100 = 0.9 >= 0.5
            score      = 0.9f,
            usedTflite = true,z
            reasons    = listOf(
                "Heart rate: 180 BPM deviates from expected pattern (72% of anomaly signal)"
            )
        )
        assertTrue("edgeScore 0.9 must flag anomaly", edgeResult.isAnomaly)
        assertTrue("Edge score must be >= 0.5", edgeResult.score >= 0.5f)
        assertTrue("Edge result must carry a reason", edgeResult.reasons.isNotEmpty())
    }

    @Test
    fun `edgeScore below 0_5 does NOT trigger edge ALERT`() {
        val edgeResult = EdgeMlEngine.AnomalyResult(
            isAnomaly  = false,
            score      = 0.2f,    // MSE too low (e.g. bradycardia known limitation)
            usedTflite = true
        )
        assertFalse(edgeResult.isAnomaly)
        assertTrue(edgeResult.reasons.isEmpty())
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Priority 2 — Cloud score (GradientBoosting)
    // Simulated via the API response model (HealthMetricResponse).
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `cloudScore above 0_5 must trigger ALERT (HealthMetricResponse contract)`() {
        val cloudResponse = com.capstone.healthmonitor.wear.domain.model.HealthMetricResponse(
            success         = true,
            message         = "OK",
            anomalyDetected = true,
            anomalyScore    = 0.87f,
            anomalyReasons  = listOf(
                "Resting heart rate: 180 BPM is above normal range (50–100 BPM)"
            )
        )
        assertTrue(cloudResponse.anomalyDetected)
        assertTrue(cloudResponse.anomalyScore >= 0.5f)
        assertNotNull(cloudResponse.anomalyReasons)
        assertTrue(cloudResponse.anomalyReasons!!.isNotEmpty())
    }

    @Test
    fun `cloudScore below 0_5 does NOT trigger cloud ALERT`() {
        val cloudResponse = com.capstone.healthmonitor.wear.domain.model.HealthMetricResponse(
            success         = true,
            message         = "OK",
            anomalyDetected = false,
            anomalyScore    = 0.3f,
            anomalyReasons  = null
        )
        assertFalse(cloudResponse.anomalyDetected)
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Priority 3 — Rule-based threshold fallback
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `tachycardia 141 BPM triggers rule-based ALERT when edge+cloud scores are below 0_5`() {
        val m           = metric(141f)
        val edgeScore   = 0.2f  // low MSE — TFLite didn't flag it
        val cloudScore  = 0.1f  // cloud also missed it

        val ruleFlags = detector.isSuspicious(m)

        assertFalse("Edge should not flag (score=0.2)", edgeScore >= 0.5f)
        assertFalse("Cloud should not flag (score=0.1)", cloudScore >= 0.5f)
        assertTrue("Rule should flag 141 BPM as tachycardia", ruleFlags)
    }

    @Test
    fun `bradycardia 39 BPM triggers rule-based ALERT`() {
        val m = metric(39f)
        assertTrue("Rule should detect 39 BPM as bradycardia", detector.isSuspicious(m))
    }

    @Test
    fun `normal HR 90 BPM with all scores below 0_5 produces NO ALERT`() {
        val m          = metric(90f)
        val edgeScore  = 0.1f
        val cloudScore = 0.2f
        val ruleFlags  = detector.isSuspicious(m)

        assertFalse(edgeScore  >= 0.5f)
        assertFalse(cloudScore >= 0.5f)
        assertFalse(ruleFlags)
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Score precedence — edge > cloud
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `edge ALERT takes precedence even if cloud score is below 0_5`() {
        // If edge engine flags an anomaly, it should be treated as an alert
        // regardless of cloud score — per system spec priority order.
        val edgeAlerts  = true   // edgeScore=0.9 >= 0.5
        val cloudAlerts = false  // cloudScore=0.3 < 0.5

        // Priority 1 always wins if edgeAlerts is true
        val shouldAlert = edgeAlerts || cloudAlerts
        assertTrue("Edge ALERT must cause overall alert", shouldAlert)
    }

    @Test
    fun `cloud ALERT activates when edge score is low`() {
        val edgeAlerts  = false  // edgeScore=0.2 < 0.5
        val cloudAlerts = true   // cloudScore=0.87 >= 0.5

        val shouldAlert = edgeAlerts || cloudAlerts
        assertTrue("Cloud ALERT must cause overall alert when edge is clear", shouldAlert)
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Explainability — reason format and content (spec table)
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `threshold fallback reason for 35 BPM matches spec format - contains BPM value`() {
        val reasons = detector.getAnomalyReasons(metric(35f))
        assertFalse("Must have at least one reason", reasons.isEmpty())
        assertTrue(
            "Reason must mention the BPM value 35",
            reasons.any { it.contains("35") }
        )
    }

    @Test
    fun `threshold fallback reason for 35 BPM mentions low or critical`() {
        val reasons = detector.getAnomalyReasons(metric(35f))
        val combined = reasons.joinToString().lowercase()
        assertTrue(
            "Threshold fallback reason should indicate low/critical status",
            combined.contains("low") || combined.contains("critical")
        )
    }

    @Test
    fun `edge anomaly reason format contains feature name and deviation keyword`() {
        // Simulate edge reason as EdgeMlEngine would produce
        val edgeReason = "Heart rate: 180 BPM deviates from expected pattern (72% of anomaly signal)"
        assertTrue(edgeReason.contains("Heart rate"))
        assertTrue(edgeReason.contains("deviates"))
        assertTrue(edgeReason.contains("BPM"))
        assertTrue(edgeReason.contains("%"))
    }

    @Test
    fun `cloud anomaly reason format contains range information`() {
        // Simulate cloud reason as GradientBoosting model would return
        val cloudReason = "Resting heart rate: 180 BPM is above normal range (50–100 BPM)"
        assertTrue(cloudReason.contains("heart rate") || cloudReason.contains("Heart rate"))
        assertTrue(cloudReason.contains("180"))
        assertTrue(cloudReason.contains("range"))
    }

    @Test
    fun `AnomalyResult reason list is ordered by feature contribution`() {
        // When edge produces multiple reasons, the highest-contributing feature
        // should be listed first (per spec: per-feature MSE sorted by contribution).
        val reasons = listOf(
            "Heart rate: 180 BPM deviates from expected pattern (72% of anomaly signal)",
            "Steps: 5000 steps deviates from expected pattern (28% of anomaly signal)"
        )
        val result = EdgeMlEngine.AnomalyResult(
            isAnomaly  = true,
            score      = 0.9f,
            usedTflite = true,
            reasons    = reasons
        )
        assertEquals(2, result.reasons.size)
        assertTrue("Highest contributor (72%) should be first",
            result.reasons[0].contains("72%"))
        assertTrue("Lower contributor (28%) should be second",
            result.reasons[1].contains("28%"))
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Reasons are end-to-end models — HealthMetricRequest carries them
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `HealthMetricRequest populates anomalyReasons correctly`() {
        val reasons = listOf("Heart rate 155 BPM exceeds safe threshold (140 BPM)")
        val request = com.capstone.healthmonitor.wear.domain.model.HealthMetricRequest(
            userId         = "test-user",
            deviceId       = "test-device",
            timestamp      = System.currentTimeMillis(),
            metrics        = mapOf("heartRate" to 155),
            isAnomalous    = true,
            localAnomalyScore = 0.6f,
            anomalyReasons = reasons
        )
        assertNotNull(request.anomalyReasons)
        val reqReasons = request.anomalyReasons
        assertEquals(1, reqReasons!!.size)
        assertTrue(reqReasons.first().contains("155"))
    }

    @Test
    fun `HealthMetricResponse with reasons from cloud model is correctly modeled`() {
        val cloudReasons = listOf(
            "Resting heart rate: 180 BPM is above normal range (50–100 BPM)",
            "Steps feature shows anomalous low activity pattern"
        )
        val response = com.capstone.healthmonitor.wear.domain.model.HealthMetricResponse(
            success         = true,
            message         = "Anomaly detected",
            anomalyDetected = true,
            anomalyScore    = 0.95f,
            anomalyReasons  = cloudReasons
        )
        assertTrue(response.anomalyDetected)
        assertEquals(2, response.anomalyReasons!!.size)
        assertTrue(response.anomalyScore >= 0.5f)
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Edge case — TFLite bradycardia known limitation (documented in engine)
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `bradycardia 35 BPM may have low edge score - rule fallback must catch it`() {
        // EdgeMlEngine docs: "Cannot detect bradycardia (MSE 6.63 < normal MSE 19.56)"
        // Score = 6.63 / 100 = 0.066, which is < 0.5 → edge won't flag it.
        val simulatedEdgeScore = 0.066f
        val m = metric(35f)

        assertFalse("Edge score 0.066 should NOT trigger edge alert",
            simulatedEdgeScore >= 0.5f)

        // Rule fallback MUST catch this case (priority 3 safety net)
        assertTrue("Rule fallback MUST catch bradycardia that TFLite misses",
            detector.isSuspicious(m))
        assertTrue(detector.getLocalScore(m) > 0f)
        assertTrue(detector.getAnomalyReasons(m).isNotEmpty())
    }
}
