# Hybrid ML Integration Guide

This document explains how the Wear OS app uses a hybrid anomaly detection approach: lightweight on-device rules + edge TFLite inference + cloud GradientBoosting inference, with **anomaly explainability** at every layer.

## Architecture

```
On-Device (LocalAnomalyDetector)
  └─ Rule-based: HR thresholds, delta spikes
     └─ Produces human-readable anomalyReasons
        └─ Feeds into EdgeMlEngine

Edge TFLite (EdgeMlEngine)
  └─ Conv1D autoencoder (~50KB, ~20ms)
     └─ Per-feature reconstruction error → anomalyReasons
        └─ Falls back to rule-based if TFLite unavailable

Cloud (Lambda – GradientBoosting)
  └─ Receives metrics with edge flags + reasons
     └─ Runs GradientBoosting (F1=0.995) inference
        └─ Returns anomaly_reasons + feature_contributions
           └─ App shows "Why?" card on watch + push notification
```

## On-Device: LocalAnomalyDetector

Located in `domain/usecase/LocalAnomalyDetector.kt`, this provides **lightweight, immediate** anomaly checks with explainability:

### Rules:
1. **Absolute Threshold**: HR ≥ 140 BPM or HR ≤ 40 BPM → suspicious
2. **Delta Check**: HR jumps by ≥ 30 BPM in one sample → suspicious

### Methods:
- `isSuspicious(metric, recent)`: Boolean — delegates to `getAnomalyReasons().isNotEmpty()`
- `getAnomalyReasons(metric, recent)`: `List<String>` — human-readable explanations
- `getLocalScore(metric, recent)`: Float 0–1 — rule-based confidence

### Example Reasons:
```
"Heart rate 180 BPM is dangerously high (threshold: 140 BPM)"
"Heart rate 35 BPM is dangerously low (threshold: 40 BPM)"
"Sudden heart rate spike: 70 → 120 BPM (50 BPM change in one reading)"
```

## Edge ML: EdgeMlEngine

Located in `domain/usecase/EdgeMlEngine.kt`, wraps TFLite models with explainability:

### AnomalyResult:
```kotlin
data class AnomalyResult(
    val isAnomaly: Boolean,
    val score: Float,                  // 0-1 anomaly score
    val modelVersion: String,          // e.g. "edge-tflite-v1" or "rule-fallback"
    val usedTflite: Boolean,
    val reasons: List<String> = emptyList()  // Explainability
)
```

### How reasons are generated:
- **TFLite path**: Per-feature reconstruction error compared to mean error; features contributing above-average signal get explanations like `"heartRate deviates from expected pattern (72% of anomaly signal)"`
- **Rule fallback**: Passes through `LocalAnomalyDetector.getAnomalyReasons()`

## Cloud: Lambda Integration

The CloudBackend Lambda uses a **GradientBoosting classifier** (F1=0.995, AUC=1.00) with full explainability.

### Request Payload (HealthMetricRequest):
```json
{
  "userId": "user_001",
  "timestamp": 1704207600000,
  "metrics": {
    "heartRate": 175.0,
    "steps": 30,
    "calories": 15.2,
    "distance": 0.1
  },
  "deviceId": "wear_SM-R910",
  "isAnomalous": true,
  "edgeAnomalyScore": 0.85,
  "localAnomalyScore": 0.8,
  "activityState": "rest",
  "modelVersion": "edge-tflite-v1",
  "anomalyReasons": ["Heart rate 175 BPM is dangerously high (threshold: 140 BPM)"]
}
```

### Lambda Inference Response:
```json
{
  "results": [{
    "metric_id": "...",
    "is_anomaly": true,
    "cloud_score": 0.97,
    "anomaly_reasons": [
      "heartRate: 175.0 BPM is above normal range (50-100 BPM)",
      "steps: 30 is below normal range (0-500) — low activity with high HR"
    ],
    "feature_contributions": {
      "heartRate": 0.72,
      "steps": 0.15,
      "calories": 0.08,
      "distance": 0.05
    }
  }],
  "model_type": "GradientBoosting",
  "model_supervised": true
}
```

### Ingestion Lambda Response (to app):
```json
{
  "success": true,
  "message": "Metric ingested and analyzed",
  "anomalyDetected": true,
  "anomalySource": "cloud",
  "cloudScore": 0.97,
  "anomalyReasons": [
    "heartRate: 175.0 BPM is above normal range (50-100 BPM)"
  ]
}
```

## Integration in Sync Worker

The `DataSyncWorker` calls `repository.syncMetricsToCloud()`, which:

1. Retrieves unsynced metrics from Room
2. For each metric:
   - Runs `edgeMlEngine.detectAnomaly(metric, recent)` → `AnomalyResult` with reasons
   - Gets rule-based score via `getLocalScore(…)`
   - Includes `anomalyReasons` in `HealthMetricRequest`
3. Sends batch to Lambda `/health-data/sync` endpoint
4. Backend returns response with `anomalyReasons` and `anomalySource`
5. Marks metrics as synced

## UI: Anomaly Alert Screen

The `AnomalyAlertScreen` (in `MainActivity.kt`) auto-navigates when an anomaly is detected:

### Anomaly Detection Logic:
```kotlin
// Check anomalyReasons from edge/cloud ML, fall back to HR threshold
val anomalyMetric = healthMetrics.firstOrNull {
    !it.anomalyReasons.isNullOrEmpty() || (it.heartRate ?: 0f) >= 140f
}
```

### Alert UI:
1. **Red alert card** — HR value, steps, average HR, timestamp
2. **"Why?" card** — Lists each anomaly reason with bullet points
3. **Action buttons** — Acknowledge, View Details (trends)
4. **Haptic feedback** — LongPress vibration on new anomaly
5. **Notification** — Shows first anomaly reason instead of generic text

## Testing Hybrid Detection

### Scenario 1: Local detection (no network)
- Device detects HR spike locally via `LocalAnomalyDetector`
- `anomalyReasons`: `["Heart rate 180 BPM is dangerously high (threshold: 140 BPM)"]`
- Haptics + notification trigger immediately with reason text
- On reconnect, sends to cloud for confirmation

### Scenario 2: Cloud refinement
- Edge flags metric (HR = 145) with reasons
- Cloud GradientBoosting confirms with score 0.95 + detailed feature contributions
- Cloud reasons replace/augment edge reasons
- Higher confidence than local rule

### Scenario 3: False positive elimination
- Local threshold flags spike (HR = 155, steps = 800, during exercise)
- Cloud scores it 0.08 → not anomalous (high activity context)
- `anomalyReasons` empty → no alert shown

## Anomaly Sources

| Source | When Used | Reason Quality |
|--------|-----------|---------------|
| `edge` | TFLite autoencoder detects anomaly | Per-feature reconstruction error |
| `threshold` | Lambda threshold fallback | Range-based ("HR above 140 BPM") |
| `cloud` | GradientBoosting inference | Feature importance + range-based |
| `rule-fallback` | TFLite unavailable on device | Same as LocalAnomalyDetector |

## Performance

### Local detector:
- `isSuspicious()` / `getAnomalyReasons()`: < 1ms
- No network overhead

### Edge TFLite:
- Inference: ~20ms
- Model size: ~50KB

### Cloud detector:
- Lambda cold start: ~1–2s
- GradientBoosting inference: ~50ms
- Network round-trip: ~500ms–2s

### Strategy:
- Edge for immediate feedback with reasons
- Cloud for authoritative scoring with feature contributions
- Persist `anomalyReasons` + `anomalySource` in DynamoDB for replay/analysis

---

**References:**
- `LocalAnomalyDetector`: `domain/usecase/LocalAnomalyDetector.kt`
- `EdgeMlEngine`: `domain/usecase/EdgeMlEngine.kt`
- `HealthMetricRequest` / `HealthMetricResponse`: `domain/model/HealthMetric.kt`
- `HealthRepository.syncMetricsToCloud()`: `data/repository/HealthRepository.kt`
- Cloud inference: `CloudBackend/aws-lambda/lambda_inference_sklearn.py`
- Cloud ingestion: `CloudBackend/aws-lambda/lambda_function.py`
