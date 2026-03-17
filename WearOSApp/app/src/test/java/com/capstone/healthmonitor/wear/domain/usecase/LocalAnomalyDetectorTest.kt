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
 * Unit tests for [LocalAnomalyDetector].
 *
 * Detection priority (matches system spec):
 *   1. Edge Score (TFLite LSTM)  >= 0.5  → ALERT
 *   2. Cloud Score (GradientBoosting) >= 0.5 → ALERT
 *   3. heartRate > 140 OR heartRate < 40    → ALERT (rule-based)  ← tested here
 *
 * LocalAnomalyDetector implements rule layer (layer 3) and provides
 * reasons used as fallback when TFLite/cloud scores are unavailable.
 */
class LocalAnomalyDetectorTest {

    private lateinit var detector: LocalAnomalyDetector

    // ── helpers ──────────────────────────────────────────────────────────────

    private fun metric(heartRate: Float?) = HealthMetric(
        userId      = "test-user",
        deviceId    = "test-device",
        timestamp   = System.currentTimeMillis(),
        heartRate   = heartRate
    )

    @Before
    fun setUp() {
        detector = LocalAnomalyDetector()
    }

    // ═══════════════════════════════════════════════════════════════════════
    // isSuspicious — threshold checks
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `normal heart rate 72 BPM is NOT suspicious`() {
        assertFalse(detector.isSuspicious(metric(72f)))
    }

    @Test
    fun `heart rate exactly at high threshold 140 BPM is suspicious`() {
        assertTrue(detector.isSuspicious(metric(140f)))
    }

    @Test
    fun `heart rate above high threshold 155 BPM is suspicious`() {
        assertTrue(detector.isSuspicious(metric(155f)))
    }

    @Test
    fun `dangerously high heart rate 180 BPM is suspicious`() {
        assertTrue(detector.isSuspicious(metric(180f)))
    }

    @Test
    fun `heart rate exactly at low threshold 40 BPM is suspicious`() {
        assertTrue(detector.isSuspicious(metric(40f)))
    }

    @Test
    fun `heart rate below low threshold 35 BPM is suspicious`() {
        assertTrue(detector.isSuspicious(metric(35f)))
    }

    @Test
    fun `heart rate just below high threshold 139 BPM is NOT suspicious`() {
        assertFalse(detector.isSuspicious(metric(139f)))
    }

    @Test
    fun `heart rate just above low threshold 41 BPM is NOT suspicious`() {
        assertFalse(detector.isSuspicious(metric(41f)))
    }

    @Test
    fun `null heart rate is NOT suspicious`() {
        assertFalse(detector.isSuspicious(metric(null)))
    }

    // ═══════════════════════════════════════════════════════════════════════
    // isSuspicious — sudden spike / drop (delta rule)
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `sudden spike of 30 BPM triggers suspicious flag`() {
        val previous = metric(80f)
        val current  = metric(110f)   // delta = 30 BPM
        assertTrue(detector.isSuspicious(current, listOf(previous)))
    }

    @Test
    fun `sudden drop of 30 BPM triggers suspicious flag`() {
        val previous = metric(100f)
        val current  = metric(70f)    // delta = 30 BPM
        assertTrue(detector.isSuspicious(current, listOf(previous)))
    }

    @Test
    fun `small delta of 10 BPM does NOT trigger suspicious flag`() {
        val previous = metric(80f)
        val current  = metric(90f)
        assertFalse(detector.isSuspicious(current, listOf(previous)))
    }

    @Test
    fun `delta of exactly 29 BPM is NOT flagged (below threshold)`() {
        val previous = metric(80f)
        val current  = metric(109f)
        assertFalse(detector.isSuspicious(current, listOf(previous)))
    }

    // ═══════════════════════════════════════════════════════════════════════
    // getAnomalyReasons — content validation
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `normal reading returns empty reasons list`() {
        val reasons = detector.getAnomalyReasons(metric(72f))
        assertTrue("Expected empty reasons for normal HR", reasons.isEmpty())
    }

    @Test
    fun `tachycardia at 155 BPM returns reason mentioning threshold 140`() {
        val reasons = detector.getAnomalyReasons(metric(155f))
        assertTrue("Should have at least one reason", reasons.isNotEmpty())
        val combined = reasons.joinToString()
        assertTrue("Reason should mention BPM value", combined.contains("155"))
        assertTrue("Reason should mention threshold", combined.contains("140"))
    }

    @Test
    fun `dangerously high 180 BPM returns reason mentioning dangerously high`() {
        val reasons = detector.getAnomalyReasons(metric(180f))
        val combined = reasons.joinToString().lowercase()
        assertTrue(
            "Reason should mention danger for 180 BPM",
            combined.contains("dangerous") || combined.contains("dangerously")
        )
    }

    @Test
    fun `bradycardia at 35 BPM returns reason mentioning critically low`() {
        val reasons = detector.getAnomalyReasons(metric(35f))
        assertTrue("Should have at least one reason", reasons.isNotEmpty())
        val combined = reasons.joinToString().lowercase()
        assertTrue(
            "Reason should mention low/critical for bradycardia",
            combined.contains("low") || combined.contains("critical")
        )
    }

    @Test
    fun `sudden spike reason mentions direction 'spike'`() {
        val reasons = detector.getAnomalyReasons(metric(115f), listOf(metric(80f)))
        val combined = reasons.joinToString().lowercase()
        assertTrue("Reason should describe a spike", combined.contains("spike"))
    }

    @Test
    fun `sudden drop reason mentions direction 'drop'`() {
        val reasons = detector.getAnomalyReasons(metric(70f), listOf(metric(105f)))
        val combined = reasons.joinToString().lowercase()
        assertTrue("Reason should describe a drop", combined.contains("drop"))
    }

    @Test
    fun `metric with both threshold AND spike violation returns multiple reasons`() {
        // HR=155 (above 140) AND jumped 80 BPM from previous 75
        val reasons = detector.getAnomalyReasons(metric(155f), listOf(metric(75f)))
        assertTrue("Should have 2 reasons (threshold + delta)", reasons.size >= 2)
    }

    // ═══════════════════════════════════════════════════════════════════════
    // getLocalScore — score range & ordering
    // ═══════════════════════════════════════════════════════════════════════

    @Test
    fun `local score for normal HR 72 BPM is 0`() {
        assertEquals(0f, detector.getLocalScore(metric(72f)), 0.001f)
    }

    @Test
    fun `local score for dangerously high 180 BPM is 1_0 (maximum)`() {
        assertEquals(1f, detector.getLocalScore(metric(180f)), 0.001f)
    }

    @Test
    fun `local score is higher for 180 BPM than for 155 BPM`() {
        val scoreExtreme  = detector.getLocalScore(metric(180f))
        val scoreHigh     = detector.getLocalScore(metric(155f))
        assertTrue("Extreme HR should score higher", scoreExtreme > scoreHigh)
    }

    @Test
    fun `local score for bradycardia 40 BPM is non-zero`() {
        assertTrue(detector.getLocalScore(metric(40f)) > 0f)
    }

    @Test
    fun `local score is always in range 0 to 1`() {
        listOf(0f, 35f, 40f, 72f, 100f, 140f, 155f, 180f, 220f).forEach { hr ->
            val score = detector.getLocalScore(metric(hr))
            assertTrue("Score $score out of range for HR $hr", score in 0f..1f)
        }
    }

    @Test
    fun `large spike from previous sample raises local score`() {
        val scoreNoHistory = detector.getLocalScore(metric(110f))
        val scoreWithSpike = detector.getLocalScore(metric(110f), listOf(metric(60f))) // delta=50
        assertTrue("Spike should raise score", scoreWithSpike >= scoreNoHistory)
    }
}
