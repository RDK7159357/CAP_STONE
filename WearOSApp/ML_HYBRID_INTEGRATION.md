# Hybrid ML Integration Guide

This document explains how the Wear OS app uses a hybrid anomaly detection approach: lightweight on-device rules + cloud LSTM inference.

## Architecture

```
On-Device (LocalAnomalyDetector)
  └─ Simple rules: HR threshold, delta detection
     └─ Flags suspicious metrics locally
        └─ Sends to cloud with flags

Cloud (Lambda)
  └─ Receives flagged metrics
     └─ Runs LSTM autoencoder inference
        └─ Returns anomaly score (0–1)
           └─ App triggers alerts based on cloud score
```

## On-Device: LocalAnomalyDetector

Located in `domain/usecase/LocalAnomalyDetector.kt`, this provides **lightweight, immediate** anomaly checks:

### Rules:
1. **Absolute Threshold**: HR ≥ 140 BPM or HR ≤ 40 BPM → suspicious
2. **Delta Check**: HR jumps by ≥ 30 BPM in one sample → suspicious

### Methods:
- `isSuspicious(metric, recent)`: Boolean—quick flag
- `getLocalScore(metric, recent)`: Float 0–1—rule-based confidence

### Usage in Repository:
```kotlin
val isAnomalous = anomalyDetector.isSuspicious(metric, recentMetrics)
val localScore = anomalyDetector.getLocalScore(metric, recentMetrics)
// Send in HealthMetricRequest
```

**When to use locally:**
- Immediate UI alert before cloud responds
- User feedback (haptics/toast) within seconds
- Offline detection if network is slow

## Cloud: Lambda Integration

Once deployed, the CloudBackend Lambda receives the sync request with flagged metrics:

### Request Payload (HealthMetricRequest):
```json
{
  "userId": "user_001",
  "timestamp": 1704207600000,
  "metrics": {
    "heartRate": 155.0,
    "steps": 120,
    "calories": 45.5,
    "batteryLevel": 85
  },
  "deviceId": "wear_SM-R910",
  "isAnomalous": true,                    // Local flag
  "localAnomalyScore": 0.8                // Local confidence (0-1)
}
```

### Lambda Handler (ingest endpoint):
1. Receive and validate request
2. If `isAnomalous == true`:
   - Load LSTM autoencoder from S3/disk
   - Extract sequence (e.g., last 30 samples)
   - Run inference: `model.predict(sequence)`
   - Get reconstruction error or anomaly probability
3. Return response with cloud score

### Response Payload (HealthMetricResponse):
```json
{
  "success": true,
  "message": "Metric ingested",
  "anomalyDetected": true,                // Final verdict
  "anomalyScore": 0.92                    // LSTM score (0-1)
}
```

## Integration in Sync Worker

The `DataSyncWorker` calls `repository.syncMetricsToCloud()`, which:

1. Retrieves unsynced metrics
2. For each metric:
   - Flags via `anomalyDetector.isSuspicious(metric, context)`
   - Gets local score via `getLocalScore(…)`
   - Includes both in `HealthMetricRequest`
3. Sends batch to Lambda `/health-data/sync` endpoint
4. Backend returns response with `anomalyScore`
5. Marks metrics as synced

## UI Handling: Cloud Scores

Currently, the MainActivity uses a simple local threshold (HR ≥ 140). To integrate cloud scores:

### Option A: Extend HealthMetric with cloud score
```kotlin
@Entity(tableName = "health_metrics")
data class HealthMetric(
    // ... existing fields
    val cloudAnomalyScore: Float? = null  // From API response
)
```
Then update HomeScreen:
```kotlin
val anomalyMetric = healthMetrics.firstOrNull { (it.cloudAnomalyScore ?: 0f) > 0.7f }
```

### Option B: Track separately in state
```kotlin
var cloudAnomalyScores: Map<Long, Float> by remember { mutableStateOf(emptyMap()) }
// Update from sync response
val anomalyMetric = healthMetrics.firstOrNull { 
    (cloudAnomalyScores[it.id] ?: 0f) > 0.7f 
}
```

## Step-by-Step Implementation

### 1. Train & export LSTM model
From `MLPipeline/models/train_lstm_autoencoder.py`:
```bash
python src/models/train_lstm_autoencoder.py
# Exports SavedModel or ONNX to saved_models/
```

### 2. Deploy Lambda with model
In CloudBackend:
```python
# lambda_function.py
import tensorflow as tf

model = tf.keras.models.load_model('path/to/saved_model')

def lambda_handler(event, context):
    for metric in event['metrics']:
        if metric['isAnomalous']:
            sequence = get_sequence(metric['userId'], metric['timestamp'])
            reconstruction = model.predict(sequence)
            anomaly_score = compute_error(sequence, reconstruction)
            metric['anomalyScore'] = float(anomaly_score)
    
    return {'success': True, 'anomalyScore': ...}
```

### 3. Update HealthMetricRequest
Already done in `domain/model/HealthMetric.kt`:
- `isAnomalous: Boolean`
- `localAnomalyScore: Float`

### 4. Update HealthMetricResponse
Already done:
- `anomalyScore: Float`

### 5. Update MainActivity (optional)
If you want cloud scores to drive UI alerts, extend the anomaly detection logic:
```kotlin
// After sync completes, use anomalyScore from response
val cloudScores = syncResponse.metrics.associate { it.id to it.anomalyScore }
val anomalyMetric = healthMetrics.firstOrNull { 
    (cloudScores[it.id] ?: 0f) > 0.7f 
}
```

## Testing Hybrid Detection

### Scenario 1: Local detection (no network)
- Device detects HR spike locally
- Haptics/notifications trigger immediately
- On reconnect, sends to cloud for confirmation

### Scenario 2: Cloud refinement
- Local threshold flags metric (HR = 145)
- Cloud LSTM scores it 0.95 → confirmed anomaly
- Higher confidence than local rule

### Scenario 3: False positive elimination
- Local threshold flags spike (HR = 142, delta +35)
- Cloud LSTM scores it 0.15 → not anomalous (e.g., user exercised)
- App can suppress alert or show different message

## Performance Tuning

### Local detector:
- `isSuspicious()`: < 1ms (simple arithmetic)
- `getLocalScore()`: < 1ms
- No network overhead

### Cloud detector:
- Lambda cold start: ~1–2s
- Inference time: depends on model size/complexity
  - Small LSTM: ~100–500ms
  - Cache model in memory for warmth
- Network round-trip: ~500ms–2s (variable)

### Strategy:
- Use local for immediate feedback
- Cloud for authoritative scoring
- Persist cloud score in Room for replay/analysis

## Next Steps

1. **Train the model**: Run `MLPipeline/src/models/train_lstm_autoencoder.py`
2. **Export**: Save as SavedModel or ONNX
3. **Deploy Lambda**: Update `CloudBackend/aws-lambda/lambda_function.py` with inference code
4. **Test end-to-end**: Generate synthetic anomalies, watch for dual detection
5. **Tune thresholds**: Adjust local rules and cloud confidence threshold (default 0.7) based on false positive rate

---

**References:**
- `LocalAnomalyDetector`: `domain/usecase/LocalAnomalyDetector.kt`
- `HealthMetricRequest`: `domain/model/HealthMetric.kt`
- `HealthRepository.syncMetricsToCloud()`: `data/repository/HealthRepository.kt`
- ML training: `MLPipeline/src/models/train_lstm_autoencoder.py`
