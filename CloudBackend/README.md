# Cloud Backend

## Overview
AWS-based serverless backend for receiving, storing, and processing health data from Wear OS devices.

## Architecture

```
API Gateway → Lambda Functions → DynamoDB
                    ↓
              ML Pipeline (SageMaker)
                    ↓
              SNS (Notifications)
```

## Components

1. **API Gateway**: RESTful API endpoints
2. **Lambda Functions**: 
   - `health-data-ingestion`: Receives and validates data
   - `anomaly-detector`: Runs ML model inference
   - `notification-sender`: Sends push notifications
3. **DynamoDB**: Time-series data storage
4. **SNS**: Push notification service

## Setup

### Prerequisites
- AWS Account
- AWS CLI installed and configured
- Python 3.9+
- Node.js (for AWS CDK, optional)

### 1. Install Dependencies

```bash
cd CloudBackend/aws-lambda
pip install -r requirements.txt -t .
```

### 2. Deploy Infrastructure

#### Option A: Using AWS CLI

```bash
# Create DynamoDB table
aws dynamodb create-table \
    --table-name HealthMetrics \
    --attribute-definitions \
        AttributeName=userId,AttributeType=S \
        AttributeName=timestamp,AttributeType=N \
    --key-schema \
        AttributeName=userId,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --stream-specification StreamEnabled=true,StreamViewType=NEW_IMAGE

# Create Lambda execution role
aws iam create-role \
    --role-name HealthMonitorLambdaRole \
    --assume-role-policy-document file://iam-policy.json

# Attach policies
aws iam attach-role-policy \
    --role-name HealthMonitorLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Deploy Lambda function
zip -r function.zip .
aws lambda create-function \
    --function-name HealthDataIngestion \
    --runtime python3.9 \
    --role arn:aws:iam::YOUR_ACCOUNT_ID:role/HealthMonitorLambdaRole \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 512

# Create API Gateway
aws apigateway create-rest-api \
    --name HealthMonitorAPI \
    --description "Health Monitoring System API"
```

#### Option B: Using AWS CDK (Recommended)

```bash
cd infrastructure
npm install
cdk deploy
```

### 3. Configure Environment Variables

```bash
aws lambda update-function-configuration \
    --function-name HealthDataIngestion \
    --environment Variables={TABLE_NAME=HealthMetrics,REGION=us-east-1}
```

### 4. Get API Endpoint

```bash
aws apigateway get-rest-apis
# Note the API ID and construct URL:
# https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/
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
    "calories": 50.2
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
Batch sync multiple metrics

**Request:**
```json
[
  {
    "userId": "user_001",
    "timestamp": 1696723200000,
    "metrics": {...},
    "deviceId": "wear_device_001"
  },
  ...
]
```

## Testing

### Test Locally

```bash
python test_lambda.py
```

### Test Deployed Function

```bash
aws lambda invoke \
    --function-name HealthDataIngestion \
    --payload file://test-payload.json \
    response.json
```

## Monitoring

### View Logs

```bash
aws logs tail /aws/lambda/HealthDataIngestion --follow
```

### CloudWatch Metrics
- Invocations
- Duration
- Errors
- Throttles

## Cost Optimization

- Use DynamoDB on-demand pricing for variable workload
- Set Lambda memory based on actual usage
- Enable Lambda reserved concurrency for predictable traffic
- Use CloudWatch Logs retention policies

## Security

1. Enable API Gateway authentication (API Key or Cognito)
2. Use VPC for Lambda functions
3. Encrypt data at rest in DynamoDB
4. Use IAM roles with least privilege
5. Enable AWS WAF for API Gateway

## Alternative: Google Cloud Setup

See `gcp-functions/` directory for Google Cloud Platform alternative.
