# Real-Time Health Monitoring System - Complete Setup Guide

## Table of Contents
1. [Environment Setup](#environment-setup)
2. [Phase 1: Wear OS App Development](#phase-1-wear-os-app)
3. [Phase 2: Cloud Backend Setup](#phase-2-cloud-backend)
4. [Phase 3: ML Pipeline](#phase-3-ml-pipeline)
5. [Phase 4: Mobile Dashboard](#phase-4-mobile-dashboard)
6. [Testing & Deployment](#testing-deployment)

---

## Environment Setup

### 1. Install Required Software

#### Android Studio (for Wear OS)
```bash
# Download from: https://developer.android.com/studio
# Install Wear OS SDK from SDK Manager
# - Android SDK Platform 30+
# - Wear OS system images
```

#### Python Environment (for ML)
```bash
# Install Python 3.8+
python3 --version

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r MLPipeline/requirements.txt
```

#### Flutter (for Dashboard)
```bash
# Download from: https://flutter.dev/docs/get-started/install
flutter doctor
```

#### Cloud CLI Tools
```bash
# For AWS
pip install awscli
aws configure

# For Google Cloud (alternative)
# Download from: https://cloud.google.com/sdk/docs/install
gcloud init
```

### 2. Create Wear OS Emulator

1. Open Android Studio → Tools → Device Manager
2. Create Device → Wear OS
3. Select: Wear OS Small Round (API 30 or higher)
4. Download system image if needed
5. Launch emulator

---

## Phase 1: Wear OS App

### Step 1.1: Create Wear OS Project

1. Open Android Studio
2. File → New → New Project
3. Select "Wear OS" → "Empty Activity"
4. Configure:
   - Name: `HealthMonitorWear`
   - Package: `com.capstone.healthmonitor.wear`
   - Language: Kotlin
   - Minimum SDK: API 30

### Step 1.2: Configure Permissions

Edit `WearOSApp/app/src/main/AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.BODY_SENSORS" />
<uses-permission android:name="android.permission.ACTIVITY_RECOGNITION" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
```

### Step 1.3: Add Dependencies

Edit `WearOSApp/app/build.gradle.kts`:
```kotlin
dependencies {
    // Health Services
    implementation("androidx.health:health-services-client:1.0.0-rc02")
    
    // Room Database
    implementation("androidx.room:room-runtime:2.6.0")
    implementation("androidx.room:room-ktx:2.6.0")
    kapt("androidx.room:room-compiler:2.6.0")
    
    // Retrofit for API calls
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    
    // Hilt Dependency Injection
    implementation("com.google.dagger:hilt-android:2.48")
    kapt("com.google.dagger:hilt-compiler:2.48")
    
    // WorkManager
    implementation("androidx.work:work-runtime-ktx:2.8.1")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
}
```

### Step 1.4: Test with Synthetic Data

Use Health Services Sensor Panel in emulator:
1. Extended Controls (...) → Virtual Sensors
2. Navigate to Health Services
3. Set Heart Rate: 75 BPM
4. Set Steps: 1000
5. Monitor app receiving data

---

## Phase 2: Cloud Backend

### Option A: AWS Setup

#### 2.1 Create DynamoDB Table
```bash
aws dynamodb create-table \
    --table-name HealthMetrics \
    --attribute-definitions \
        AttributeName=userId,AttributeType=S \
        AttributeName=timestamp,AttributeType=N \
    --key-schema \
        AttributeName=userId,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST
```

#### 2.2 Create Lambda Function
```bash
cd CloudBackend/aws-lambda
zip -r function.zip .
aws lambda create-function \
    --function-name HealthDataIngestion \
    --runtime python3.9 \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip
```

#### 2.3 Create API Gateway
```bash
aws apigateway create-rest-api \
    --name HealthMonitorAPI \
    --description "API for health monitoring system"
```

### Option B: Google Cloud Setup (Alternative)

```bash
# Deploy Cloud Function
cd CloudBackend/gcp-functions
gcloud functions deploy healthDataIngestion \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated

# Create Firestore database
gcloud firestore databases create --region=us-central
```

---

## Phase 3: ML Pipeline

### 3.1 Data Preprocessing

```bash
cd MLPipeline
python src/preprocessing/data_cleaner.py
```

### 3.2 Train Baseline Model

```bash
# Train Isolation Forest
python src/models/train_isolation_forest.py

# Train LSTM Autoencoder
python src/models/train_lstm_autoencoder.py
```

### 3.3 Deploy Model to Cloud

#### AWS SageMaker
```bash
python src/deployment/deploy_to_sagemaker.py
```

#### Google Cloud AI Platform
```bash
gcloud ai-platform models create health_anomaly_detector
gcloud ai-platform versions create v1 \
    --model health_anomaly_detector \
    --runtime-version 2.11 \
    --python-version 3.8 \
    --framework tensorflow
```

---

## Phase 4: Mobile Dashboard

### 4.1 Create Flutter Project

```bash
cd MobileDashboard
flutter create health_monitor_dashboard
cd health_monitor_dashboard
```

### 4.2 Add Dependencies

Edit `pubspec.yaml`:
```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  provider: ^6.0.5
  fl_chart: ^0.65.0
  firebase_messaging: ^14.7.6
  firebase_core: ^2.24.2
```

### 4.3 Setup Firebase for Notifications

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login and initialize
firebase login
firebase init

# Add Firebase to Flutter app
flutterfire configure
```

### 4.4 Run Dashboard

```bash
flutter run
```

---

## Testing & Deployment

### End-to-End Test Scenario

1. **Generate Synthetic Data on Emulator**
   - Set Heart Rate: 155 BPM (abnormally high)
   - Duration: 10 minutes

2. **Verify Data Flow**
   ```bash
   # Check cloud logs
   aws logs tail /aws/lambda/HealthDataIngestion --follow
   ```

3. **Verify Anomaly Detection**
   ```bash
   # Check ML model output
   python MLPipeline/src/test_realtime_detection.py
   ```

4. **Verify Alert Received**
   - Check mobile app for push notification
   - Verify dashboard shows anomaly flag

### Performance Optimization

1. **Wear OS Battery Optimization**
   - Batch data uploads (every 1-2 minutes)
   - Use WorkManager for background sync
   - Minimize sensor polling frequency

2. **Cloud Latency Optimization**
   - Use Lambda provisioned concurrency
   - Enable CloudFront caching for API
   - Optimize ML model inference time

3. **ML Model Optimization**
   - Use TensorFlow Lite for edge deployment
   - Quantize models for faster inference
   - Implement model caching

---

## Troubleshooting

### Wear OS App Issues

**Problem**: Permissions not granted
```kotlin
// Add runtime permission request
if (checkSelfPermission(BODY_SENSORS) != PERMISSION_GRANTED) {
    requestPermissions(arrayOf(BODY_SENSORS), REQUEST_CODE)
}
```

**Problem**: Health Services not available
```kotlin
val availabilityStatus = healthServicesClient.checkAvailability()
```

### Cloud Backend Issues

**Problem**: CORS errors
```python
# Add CORS headers to Lambda response
headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST,OPTIONS'
}
```

### ML Pipeline Issues

**Problem**: Model overfitting
```python
# Add dropout and regularization
model.add(Dropout(0.2))
model.add(Dense(128, kernel_regularizer=l2(0.001)))
```

---

## Next Steps

1. ✅ Complete Phase 1: Wear OS data collection
2. ✅ Complete Phase 2: Cloud integration
3. ✅ Complete Phase 3: ML model training
4. ✅ Complete Phase 4: Dashboard development
5. 🔄 Integration testing
6. 🔄 Performance optimization
7. 🔄 User acceptance testing
8. 🔄 Production deployment

## Resources

- [Health Services API Documentation](https://developer.android.com/training/wearables/health-services)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [TensorFlow Time Series Tutorial](https://www.tensorflow.org/tutorials/structured_data/time_series)
- [Flutter Firebase Setup](https://firebase.flutter.dev/docs/overview)
