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
  "userId": "user_001",
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

**Response:**
```json
{
  "success": true,
  "message": "Data ingested successfully",
  "anomalyDetected": false
}
```

### POST /health-data/sync
Batch sync multiple metrics from Wear OS

### GET /health-data/history
Get historical metrics for a user

### POST /notifications/register
Register push notification token

## Anomaly Detection Flow

```
1. Wear OS sends metrics → API Gateway
2. HealthDataIngestion Lambda stores to DynamoDB
3. HealthDataIngestion invokes HealthAnomalyInference Lambda (direct invocation)
4. HealthAnomalyInference:
   a. Parses event — supports both API Gateway (body wrapper) and direct invocation (raw payload)
   b. Downloads GradientBoosting model from S3 (cached after first call)
   c. Applies StandardScaler normalization
   d. Runs model.predict_proba() for anomaly probability
   e. Returns is_anomaly + cloud_score (0-1)
5. If anomaly detected → publishes to SNS → push notification
```

**Inference Response:**
```json
{
  "results": [
    {
      "metric_id": "abc123",
      "is_anomaly": true,
      "cloud_score": 0.97,
      "model_type": "GradientBoostingClassifier"
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
curl -X POST https://YOUR-API-ID.execute-api.ap-south-2.amazonaws.com/prod/health-data/ingest \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -d '{"userId": "test", "timestamp": 1708300800000, "deviceId": "test", "metrics": {"heartRate": 175, "steps": 30, "calories": 15, "distance": 0.1}}'
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
docker tag health-inference-lambda:latest <ECR_URI>:latest
docker push <ECR_URI>:latest
aws lambda update-function-code --function-name HealthAnomalyInference \
    --image-uri <ECR_URI>:latest --region ap-south-2

# 4. Clear Lambda cache (force re-download)
# The model is cached in /tmp, so updating the Lambda or waiting for cold start works
```

> **Important**: The container's numpy version must match the training environment.
> Currently `requirements-layer.txt` pins `numpy>=2.0.0` to match numpy 2.x used during training.

## Security

1. API Gateway authentication via API Key
2. IAM roles with least privilege
3. S3 model bucket with read-only Lambda access
4. Encrypted data at rest in DynamoDB
5. CORS configured for allowed origins
