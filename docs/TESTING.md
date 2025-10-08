# Testing Guide

## Overview
Comprehensive testing strategy for the Real-Time Health Monitoring System.

## Test Environment Setup

### 1. Wear OS Testing Environment

```bash
# Create Wear OS emulator with synthetic sensors
# Android Studio → Tools → Device Manager → Create Device

# Enable Health Services testing
adb shell settings put global health_services_test_mode 1
```

### 2. Cloud Testing Environment

```bash
# Setup AWS test account
aws configure --profile test

# Deploy to test environment
./deploy.sh --environment test
```

### 3. ML Testing Environment

```bash
cd MLPipeline
python -m pytest tests/
```

## Testing Phases

### Phase 1: Unit Testing

#### Wear OS App
```kotlin
// Test Health Services data collection
@Test
fun testHeartRateCollection() {
    // Mock Health Services client
    // Verify data is collected correctly
}

@Test
fun testDataPersistence() {
    // Test Room database operations
}
```

Run tests:
```bash
cd WearOSApp
./gradlew test
./gradlew connectedAndroidTest
```

#### Cloud Backend
```python
# Test Lambda function locally
def test_health_data_ingestion():
    event = {
        'body': json.dumps({
            'userId': 'test_user',
            'timestamp': 1234567890,
            'metrics': {'heartRate': 75}
        })
    }
    result = lambda_handler(event, {})
    assert result['statusCode'] == 200
```

Run tests:
```bash
cd CloudBackend/aws-lambda
python -m pytest tests/
```

#### ML Pipeline
```python
# Test preprocessing
def test_data_preprocessing():
    df = generate_synthetic_data(100)
    preprocessor = HealthDataPreprocessor()
    result = preprocessor.preprocess(df, fit=True)
    assert result.shape[0] == 100

# Test model training
def test_model_training():
    model = LSTMAutoencoder(60, 10)
    model.build_model()
    assert model.model is not None
```

Run tests:
```bash
cd MLPipeline
pytest tests/ -v --cov=src
```

### Phase 2: Integration Testing

#### Test Data Flow: Wear OS → Cloud

1. **Setup Test User**
```bash
# Configure test user credentials
export TEST_USER_ID="test_user_001"
export TEST_DEVICE_ID="wear_test_001"
```

2. **Generate Test Data on Emulator**
```bash
# Use Health Services sensor panel
# Or use ADB commands
adb shell "settings put global heart_rate 155"
```

3. **Verify Cloud Reception**
```bash
# Check DynamoDB
aws dynamodb query \
    --table-name HealthMetrics \
    --key-condition-expression "userId = :uid" \
    --expression-attribute-values '{":uid":{"S":"test_user_001"}}'

# Check Lambda logs
aws logs tail /aws/lambda/HealthDataIngestion --follow
```

#### Test Data Flow: Cloud → ML → Alert

1. **Inject Test Data**
```bash
curl -X POST https://your-api.com/health-data/ingest \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-key' \
  -d '{
    "userId": "test_user",
    "timestamp": 1696723200000,
    "metrics": {"heartRate": 175},
    "deviceId": "test_device"
  }'
```

2. **Verify ML Detection**
```bash
cd MLPipeline
python src/test_realtime_detection.py --user-id test_user
```

3. **Check Alert Sent**
```bash
# Check Firebase Cloud Messaging logs
# Verify mobile app received notification
```

### Phase 3: End-to-End Testing

#### Scenario 1: Normal Activity
```
1. Start Wear OS app
2. Set normal heart rate (70 BPM)
3. Wait 5 minutes
4. Verify:
   - Data stored in Room database
   - Data synced to cloud
   - No anomaly alerts
   - Dashboard shows normal status
```

#### Scenario 2: Anomaly Detection
```
1. Start Wear OS app
2. Set high heart rate (165 BPM)
3. Maintain for 10 minutes
4. Verify:
   - Data collected every 5 seconds
   - Cloud receives data
   - ML model detects anomaly
   - Alert sent to mobile app
   - Dashboard shows anomaly flag
5. Check timing:
   - Alert should arrive within 30 seconds
```

#### Scenario 3: Network Interruption
```
1. Start Wear OS app
2. Disable network on emulator
3. Generate data for 5 minutes
4. Verify:
   - Data buffered locally
5. Re-enable network
6. Verify:
   - Buffered data synced
   - No data loss
```

#### Scenario 4: Battery Optimization
```
1. Monitor battery level
2. Run app for 1 hour
3. Verify:
   - Battery drain < 5%
   - Data collection continues
   - Background sync efficient
```

### Phase 4: Performance Testing

#### Load Testing

```python
# Test cloud backend with concurrent requests
import asyncio
import aiohttp

async def send_request(session, user_id):
    data = {
        'userId': user_id,
        'timestamp': int(time.time() * 1000),
        'metrics': {'heartRate': random.randint(60, 100)}
    }
    async with session.post(API_URL, json=data) as response:
        return await response.json()

async def load_test(num_requests=1000):
    async with aiohttp.ClientSession() as session:
        tasks = [send_request(session, f'user_{i}') for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
    return results

# Run test
results = asyncio.run(load_test(1000))
```

#### Latency Testing

```bash
# Measure end-to-end latency
time curl -X POST https://your-api.com/health-data/ingest \
  -H 'Content-Type: application/json' \
  -d @test-payload.json
```

Target: < 500ms for 95th percentile

#### ML Model Inference Speed

```python
import time

def test_inference_speed(model, test_data, num_runs=100):
    times = []
    for _ in range(num_runs):
        start = time.time()
        model.predict(test_data)
        times.append(time.time() - start)
    
    print(f"Mean: {np.mean(times)*1000:.2f}ms")
    print(f"95th percentile: {np.percentile(times, 95)*1000:.2f}ms")

test_inference_speed(autoencoder, X_test)
```

Target: < 100ms per inference

### Phase 5: Security Testing

#### Authentication Testing
```bash
# Test without API key (should fail)
curl -X POST https://your-api.com/health-data/ingest \
  -H 'Content-Type: application/json' \
  -d @test-payload.json

# Test with invalid API key (should fail)
curl -X POST https://your-api.com/health-data/ingest \
  -H 'X-API-Key: invalid-key' \
  -d @test-payload.json

# Test with valid API key (should succeed)
curl -X POST https://your-api.com/health-data/ingest \
  -H 'X-API-Key: valid-key' \
  -d @test-payload.json
```

#### Data Encryption Testing
```python
# Verify data is encrypted at rest
def test_data_encryption():
    # Check DynamoDB encryption settings
    response = dynamodb.describe_table(TableName='HealthMetrics')
    assert response['Table']['SSEDescription']['Status'] == 'ENABLED'
```

#### SQL Injection Testing
```bash
# Try SQL injection payloads (should be sanitized)
curl -X POST https://your-api.com/health-data/ingest \
  -H 'Content-Type: application/json' \
  -d '{"userId":"user\"; DROP TABLE users;--"}'
```

### Phase 6: User Acceptance Testing

#### Test Scenarios

1. **First-time User Setup**
   - Install app
   - Grant permissions
   - View onboarding
   - Start monitoring

2. **Daily Usage**
   - View current metrics
   - Check history
   - Respond to alerts
   - View trends

3. **Alert Response**
   - Receive anomaly alert
   - View details
   - Take action
   - Dismiss alert

#### Feedback Collection
```
- Usability survey
- Performance feedback
- Feature requests
- Bug reports
```

## Test Data

### Synthetic Test Datasets

1. **Normal Data** (10,000 samples)
   - Heart rate: 60-100 BPM
   - Circadian rhythm pattern
   - No anomalies

2. **Anomalous Data** (1,000 samples)
   - 10% anomaly rate
   - Types: High HR, Low HR, Sudden change

3. **Edge Cases**
   - Missing values
   - Extreme values
   - Rapid changes
   - Extended periods

### Test User Accounts

```
test_user_001: Normal user
test_user_002: User with anomalies
test_user_003: High activity user
test_user_004: Low activity user
```

## Test Automation

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on: [push, pull_request]

jobs:
  test-wearos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: ./gradlew test
      
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Lambda tests
        run: |
          pip install -r requirements.txt
          pytest tests/
      
  test-ml:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run ML tests
        run: |
          cd MLPipeline
          pip install -r requirements.txt
          pytest tests/
```

## Test Metrics

### Coverage Targets
- Unit test coverage: >80%
- Integration test coverage: >70%
- Critical path coverage: 100%

### Performance Targets
- API latency: <500ms (95th percentile)
- ML inference: <100ms
- Battery drain: <5% per hour
- Data sync success: >99%

### Quality Targets
- ML precision: >90%
- ML recall: >85%
- False positive rate: <10%
- App crash rate: <0.1%

## Test Reports

Generate comprehensive test reports:

```bash
# Wear OS test report
./gradlew testDebugUnitTest --tests "*" --info

# Backend coverage report
pytest --cov=lambda_function --cov-report=html

# ML model evaluation report
python src/evaluation/generate_report.py
```

## Troubleshooting Tests

### Common Test Failures

1. **Emulator not responding**
   ```bash
   adb kill-server
   adb start-server
   ```

2. **Lambda test timeout**
   - Increase timeout in test configuration
   - Check network connectivity

3. **ML test memory error**
   - Reduce batch size
   - Use smaller test dataset

4. **Integration test fails**
   - Check all services are running
   - Verify credentials
   - Check network configuration
