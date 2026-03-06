# Cloud Backend

## Overview
AWS-based serverless backend for receiving, storing, and processing health data from Wear OS devices.

## Architecture

```
API Gateway → Lambda Functions → DynamoDB
                    ↓
              ML Inference Lambda
              (GradientBoosting Classifier)
                    ↓
              SNS (Notifications)
```

## ML Model

**Best Model: GradientBoosting Classifier** (updated Mar 2026)

| Metric | Value |
|--------|:-----:|
| F1-Score | **0.9950** |
| AUC-ROC | 1.0000 |
| Precision | 0.9934 |
| Recall | 0.9967 |
| 5-fold CV F1 | 0.9950 ± 0.0016 |

- **Model file**: `best_anomaly_gradientboosting.pkl`
- **Scaler file**: `best_anomaly_scaler.pkl`
- **S3 path**: `s3://health-ml-models/gradientboosting/`
- **Features**: heartRate, steps, calories, distance
- **Type**: Supervised GradientBoostingClassifier (100 estimators, max_depth=4)
- **Previous model**: Random Forest (F1=1.00, but overfitting risk) → GradientBoosting selected for generalization

## Components

1. **API Gateway**: RESTful API endpoints with API key authentication
2. **Lambda Functions**: 
   - `HealthDataIngestion`: Receives, validates, and stores health data
   - `HealthAnomalyInference`: Runs GradientBoosting anomaly detection (container, 1024MB)
   - `HealthSnsToExpo`: Sends push notifications via Expo
   - `HealthReadMetrics`: Reads metrics for dashboard
3. **DynamoDB Tables**:
   - `HealthMetrics`: Time-series health data (userId + timestamp)
   - `HealthPushTokens`: Push notification tokens (userId + deviceId)
4. **S3 Bucket**: `health-ml-models` for model artifacts
5. **SNS Topic**: `health-alerts` for multi-channel notifications

## Setup

### Prerequisites
- AWS Account
- AWS CLI installed and configured
- Python 3.9+
- Docker (for building inference Lambda container)

### 1. Deploy Everything (One Command)

```bash
cd CloudBackend/aws-lambda
./deploy.sh
```

This automatically:
1. Creates DynamoDB tables
2. Creates IAM roles and policies
3. Builds and pushes inference Docker image to ECR
4. Uploads GradientBoosting model to S3
5. Creates/updates all Lambda functions
6. Sets up API Gateway with routes
7. Creates SNS topic and subscriptions
8. Outputs API endpoint and API key

### 2. Install Dependencies (Local Testing)

```bash
cd CloudBackend/aws-lambda
pip install -r requirements.txt
```

## API Endpoints

### POST /health-data/ingest
Ingest single health metric

**Request:**
```json
{
  "userId": "demo-user-dhanush",
  "timestamp": 1696723200000,
  "metrics": {
    "heartRate": 75.5,
    "steps": 1000,
    "calories": 50.2,
    "distance": 0.3
  },
  "deviceId": "wear_device_001"
}
```

**Response (normal):**
```json
{
  "success": true,
  "message": "Data ingested successfully",
  "anomalyDetected": false,
  "anomalySource": "none",
  "cloudScore": 0.02,
  "anomalyReasons": []
}
```

**Response (anomaly detected):**
```json
{
  "success": true,
  "message": "Data ingested successfully",
  "anomalyDetected": true,
  "anomalySource": "cloud",
  "cloudScore": 0.97,
  "anomalyReasons": [
    "Resting heart rate: 180 BPM is above normal range (50–100 BPM)"
  ]
}
```

### POST /health-data/sync
Batch sync multiple metrics from Wear OS

### GET /health/metrics
Get latest metrics for a user (used by Mobile Dashboard)

**Query Parameters:**
- `userId` (required): User identifier
- `limit` (optional): Number of records (default 50)

**Response:**
```json
{
  "success": true,
  "count": 2,
  "metrics": [
    {
      "timestamp": 1696723200000,
      "heartRate": 180,
      "anomalyDetected": true,
      "anomalySource": "cloud",
      "anomalyReasons": ["Resting heart rate: 180 BPM is above normal range (50–100 BPM)"],
      "cloudAnomalyScore": 0.97
    }
  ]
}
```

### GET /health-data/history
Get historical metrics for a user

**Query Parameters:**
- `userId` (required): User identifier
- `startDate` / `endDate` (optional): Filter by date range (ISO format)
- `limit` (optional): Max records (default 100)

### POST /notifications/register
Register push notification token

## Anomaly Detection Flow

```
1. Wear OS sends metrics → API Gateway
   (includes edge anomaly score + anomalyReasons from on-device ML)
2. HealthDataIngestion Lambda stores to DynamoDB
3. HealthDataIngestion invokes HealthAnomalyInference Lambda (direct invocation)
4. HealthAnomalyInference:
   a. Parses event — supports both API Gateway (body wrapper) and direct invocation (raw payload)
   b. Downloads GradientBoosting model from S3 (cached after first call)
   c. Applies StandardScaler normalization
   d. Runs model.predict_proba() for anomaly probability
   e. Generates human-readable anomaly explanations:
      - Range-based: compares each metric against normal ranges
      - Feature-importance-weighted: uses GradientBoosting feature_importances_
        to compute per-feature contribution percentages
   f. Returns is_anomaly + cloud_score + anomaly_reasons + feature_contributions
5. If anomaly detected:
   a. anomalyReasons stored in DynamoDB alongside the metric
   b. SNS notification includes the top reason as push body
      (e.g. "Heart rate 180 BPM is dangerously high" instead of generic alert)
6. Mobile dashboard reads metrics via HealthReadMetrics Lambda
   → anomalyReasons and anomalySource returned to UI
```

### Anomaly Explainability

The system provides three levels of anomaly explanation:

| Source | Method | Example Output |
|--------|--------|----------------|
| **Edge (TFLite)** | Per-feature reconstruction error contribution | "Heart rate: 180 BPM deviates from expected pattern (72% of anomaly signal)" |
| **Edge (Rules)** | Threshold violation descriptions | "Heart rate 180 BPM is dangerously high (threshold: 140 BPM)" |
| **Cloud (GradientBoosting)** | Range check + feature importance weighting | "Resting heart rate: 180 BPM is above normal range (50–100 BPM)" |
| **Threshold fallback** | Simple range checks | "Heart rate 35 BPM is dangerously low (normal: 50–100 BPM)" |

**Normal ranges used for explanations:**

| Feature | Normal Range | Unit |
|---------|:----------:|------|
| heartRate | 50–100 | BPM |
| steps | 0–500 | steps/interval |
| calories | 0–150 | kcal/interval |
| distance | 0–2.0 | km/interval |

**Inference Response:**
```json
{
  "results": [
    {
      "metric_id": "abc123",
      "is_anomaly": true,
      "cloud_score": 0.97,
      "model_type": "GradientBoostingClassifier",
      "anomaly_reasons": [
        "Resting heart rate: 180 BPM is above normal range (50–100 BPM)"
      ],
      "feature_contributions": {
        "heartRate": 0.7214,
        "steps": 0.1523,
        "calories": 0.0891,
        "distance": 0.0372
      }
    }
  ],
  "model_type": "GradientBoostingClassifier",
  "model_supervised": true
}
```

## Testing

### Test Deployed Function

The inference Lambda supports both direct invocation (raw payload) and API Gateway events (body wrapper):

```bash
# Direct invocation (same format the ingestion Lambda uses)
aws lambda invoke \
    --function-name HealthAnomalyInference \
    --cli-binary-format raw-in-base64-out \
    --payload '{"metrics": [{"metric_id": "test:1", "heart_rate": 175, "steps": 30, "calories": 15, "distance": 0.1}]}' \
    response.json --region ap-south-2

cat response.json
```

### Test API Endpoint

```bash
curl -X POST https://u8tkgz3vsf.execute-api.ap-south-2.amazonaws.com/prod/health-data/ingest \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -d '{"userId": "demo-user-dhanush", "timestamp": 1708300800000, "deviceId": "test", "metrics": {"heartRate": 175, "steps": 30, "calories": 15, "distance": 0.1}}'
```
```

## Monitoring

```bash
# View Lambda logs
aws logs tail /aws/lambda/HealthAnomalyInference --follow --region ap-south-2

# Check function config
aws lambda get-function --function-name HealthAnomalyInference --region ap-south-2
```

## Updating the Model

To deploy a new model version:

```bash
# 1. Run comprehensive tests to train best model
cd ../../MLPipeline
source venv/bin/activate
python src/tests/comprehensive_ml_test.py

# 2. Upload to S3
aws s3 cp models/saved_models/best_anomaly_gradientboosting.pkl \
    s3://health-ml-models/gradientboosting/model.pkl --region ap-south-2

aws s3 cp models/saved_models/best_anomaly_scaler.pkl \
    s3://health-ml-models/gradientboosting/scaler.pkl --region ap-south-2

# 3. Rebuild and push container (ensure numpy version matches training env)
cd ../CloudBackend/aws-lambda
docker build --platform linux/amd64 -f Dockerfile.inference -t health-inference-lambda:latest .
docker tag health-inference-lambda:latest 145023117892.dkr.ecr.ap-south-2.amazonaws.com/health-inference-lambda:latest
docker push 145023117892.dkr.ecr.ap-south-2.amazonaws.com/health-inference-lambda:latest
aws lambda update-function-code --function-name HealthAnomalyInference \
    --image-uri 145023117892.dkr.ecr.ap-south-2.amazonaws.com/health-inference-lambda:latest --region ap-south-2

# 4. Clear Lambda cache (force re-download)
# The model is cached in /tmp, so updating the Lambda or waiting for cold start works
```

> **Important**: The container's numpy version must match the training environment.
> Currently `requirements-layer.txt` pins `numpy>=2.0.0` to match numpy 2.x used during training.

## DynamoDB Schema

### HealthMetrics Table

| Field | Type | Description |
|-------|------|-------------|
| `userId` (PK) | String | User identifier |
| `timestamp` (SK) | Number | Unix timestamp in ms |
| `deviceId` | String | Source device identifier |
| `metrics` | Map | Raw health metric values |
| `anomalyDetected` | Boolean | Whether any anomaly was flagged |
| `localAnomalyScore` | Number | Rule-based score from Wear OS (0–1) |
| `edgeAnomalyScore` | Number | TFLite model score from Wear OS (0–1) |
| `cloudAnomalyScore` | Number | GradientBoosting probability (0–1) |
| `cloudAnomalyDetected` | Boolean | Cloud model prediction |
| `activityState` | String | Activity classification (sleep/rest/walk/run/exercise/other) |
| `anomalyReasons` | List\<String\> | Human-readable explanations of anomaly |
| `modelVersion` | String | Edge model version identifier |

## Security

1. API Gateway authentication via API Key
2. IAM roles with least privilege
3. S3 model bucket with read-only Lambda access
4. Encrypted data at rest in DynamoDB
5. CORS configured for allowed origins

## Demo Data

The database contains **42 realistic demo records** for userId `demo-user-dhanush` spanning 24 hours, including:

| Episode | Time | Type | Heart Rate | Anomaly Reasons |
|---------|------|------|:----------:|-----------------|
| Normal | Throughout day | Varied activities | 55–98 BPM | — |
| Tachycardia | ~3:30 PM | Exercise spike | 155–178 BPM | "Elevated heart rate: 178 BPM is above normal range" |
| Bradycardia | ~8:30 PM | Sleep dip | 38–42 BPM | "Low heart rate: 38 BPM is below normal range" |
| Dangerous spike | ~10:15 PM | Stress event | 185–195 BPM | "Dangerous heart rate: 195 BPM exceeds safe threshold" |

Query demo data:
```bash
curl "https://u8tkgz3vsf.execute-api.ap-south-2.amazonaws.com/prod/health/metrics?userId=demo-user-dhanush&limit=50" \
  -H "X-API-Key: YOUR_API_KEY"
```
