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

#### Node.js and Expo (for Dashboard)
```bash
# Install Node.js 16+ from: https://nodejs.org/
node --version
npm --version

# Install Expo CLI globally
npm install -g expo-cli
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

### Step 1.4: Setup TensorFlow Lite for Wear OS

Add TFLite dependencies in `build.gradle.kts`:
```kotlin
dependencies {
    // TensorFlow Lite
    implementation("org.tensorflow:tensorflow-lite:2.14.0")
    implementation("org.tensorflow:tensorflow-lite-gpu:2.14.0")
    implementation("org.tensorflow:tensorflow-lite-support:0.4.4")
}
```

Create `TFLiteModelLoader.kt`:
```kotlin
class TFLiteModelLoader(private val context: Context) {
    private var activityClassifier: Interpreter? = null
    private var anomalyDetector: Interpreter? = null
    
    fun loadModels() {
        activityClassifier = Interpreter(
            loadModelFile("activity_classifier.tflite")
        )
        anomalyDetector = Interpreter(
            loadModelFile("anomaly_detector.tflite")
        )
    }
    
    private fun loadModelFile(filename: String): ByteBuffer {
        val fileDescriptor = context.assets.openFd(filename)
        val inputStream = FileInputStream(fileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        val startOffset = fileDescriptor.startOffset
        val declaredLength = fileDescriptor.declaredLength
        return fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
    }
}
```

### Step 1.5: Implement ML-Based Activity Classifier

Create `MLActivityClassifier.kt`:
```kotlin
class MLActivityClassifier(private val interpreter: Interpreter) {
    // Input: 100 samples x 6 features (accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z)
    private val inputBuffer = Array(1) { Array(100) { FloatArray(6) } }
    private val outputBuffer = Array(1) { FloatArray(6) } // 6 activity classes
    
    fun classifyActivity(sensorWindow: List<SensorData>): ActivityState {
        // Prepare input tensor
        sensorWindow.forEachIndexed { i, data ->
            inputBuffer[0][i][0] = data.accelX
            inputBuffer[0][i][1] = data.accelY
            inputBuffer[0][i][2] = data.accelZ
            inputBuffer[0][i][3] = data.gyroX
            inputBuffer[0][i][4] = data.gyroY
            inputBuffer[0][i][5] = data.gyroZ
        }
        
        // Run inference
        interpreter.run(inputBuffer, outputBuffer)
        
        // Get prediction
        val predictions = outputBuffer[0]
        val activityIndex = predictions.indices.maxByOrNull { predictions[it] } ?: 0
        
        return ActivityState.values()[activityIndex]
    }
}

enum class ActivityState {
    SLEEPING, RESTING, WALKING, RUNNING, EXERCISING, OTHER
}
```

### Step 1.6: Implement Personal Baseline Engine

Create `PersonalBaselineEngine.kt`:
```kotlin
class PersonalBaselineEngine {
    // Store 7-day rolling window
    private val baselineWindow = mutableListOf<HealthSnapshot>()
    
    fun updateBaseline(data: HealthSnapshot) {
        baselineWindow.add(data)
        // Keep only last 7 days
        if (baselineWindow.size > 7 * 24 * 12) { // 5-sec intervals
            baselineWindow.removeFirst()
        }
    }
    
    fun getPersonalRanges(activityState: ActivityState): HealthRanges {
        val filtered = baselineWindow.filter { it.activity == activityState }
        return HealthRanges(
            hrMin = filtered.map { it.heartRate }.percentile(5),
            hrMax = filtered.map { it.heartRate }.percentile(95),
            // ... similar for other metrics
        )
    }
}
```

### Step 1.7: Implement ML-Powered Anomaly Detector

Create `MLAnomalyDetector.kt`:
```kotlin
class MLAnomalyDetector(
    private val interpreter: Interpreter,
    private val baselineEngine: PersonalBaselineEngine
) {
    // Input: 50 timesteps x 4 features (hr, steps, activity_encoded, baseline_deviation)
    private val inputBuffer = Array(1) { Array(50) { FloatArray(4) } }
    private val outputBuffer = Array(1) { FloatArray(1) } // Anomaly score
    
    fun detectAnomaly(
        timeSeriesWindow: List<HealthSnapshot>,
        activity: ActivityState
    ): AnomalyResult? {
        val baseline = baselineEngine.getPersonalRanges(activity)
        
        // Prepare input: combine raw data + baseline deviation
        timeSeriesWindow.forEachIndexed { i, snapshot ->
            inputBuffer[0][i][0] = snapshot.heartRate.toFloat()
            inputBuffer[0][i][1] = snapshot.steps.toFloat()
            inputBuffer[0][i][2] = activity.ordinal.toFloat()
            inputBuffer[0][i][3] = (snapshot.heartRate - baseline.hrMean).toFloat()
        }
        
        // Run LSTM inference
        interpreter.run(inputBuffer, outputBuffer)
        
        val anomalyScore = outputBuffer[0][0]
        
        return when {
            anomalyScore > 0.8 -> AnomalyResult.Critical(
                "High anomaly score ($anomalyScore) for $activity state",
                score = anomalyScore,
                confidence = anomalyScore
            )
            anomalyScore > 0.6 -> AnomalyResult.Warning(
                "Moderate anomaly detected",
                score = anomalyScore,
                confidence = anomalyScore
            )
            else -> null
        }
    }
}

sealed class AnomalyResult {
    data class Critical(val message: String, val score: Float, val confidence: Float) : AnomalyResult()
    data class Warning(val message: String, val score: Float, val confidence: Float) : AnomalyResult()
}
```

### Step 1.8: Test with Synthetic Data & ML Models

Use Health Services Sensor Panel in emulator:
1. Extended Controls (...) → Virtual Sensors
2. Navigate to Health Services
3. **Test Scenario 1: Normal Resting (Baseline Learning)**
   - Set HR: 75 BPM, Low movement → ML should classify as RESTING
4. **Test Scenario 2: Exercise (Active State)**
   - Set HR: 150 BPM, High movement → ML should classify as EXERCISING
5. **Test Scenario 3: ML Anomaly Detection**
   - Set HR: 155 BPM, NO movement → **ML should detect anomaly with high score!**
6. Monitor on-device ML inference logs:
   ```
   Activity Classifier: RESTING (confidence: 0.95, latency: 45ms)
   Anomaly Detector: CRITICAL (score: 0.87, latency: 92ms)
   ```

---

## Phase 2: Cloud Backend (ML Training & Data Sync)

**Purpose**: The cloud backend provides:
- Real-time data ingestion and storage
- ML model training infrastructure (SageMaker)
- Advanced analytics and insights
- Mobile dashboard API
- Model deployment to edge devices

### Option A: AWS Setup

#### 2.1 Create DynamoDB Table for Time-Series Storage
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

## Phase 3: ML Pipeline (Model Training & Deployment)

**This phase is REQUIRED** for the hybrid edge-cloud ML system:
- Train models in cloud (TensorFlow/Keras)
- Convert to TensorFlow Lite for edge deployment
- Deploy optimized models to Wear OS devices

### 3.1 Train Activity Classification Model

```bash
cd MLPipeline

# Generate or collect training data
python src/data/generate_synthetic_data.py --activity-data

# Train CNN-LSTM activity classifier
python src/models/train_activity_classifier.py \
    --data data/processed/activity_data.csv \
    --epochs 50 \
    --batch-size 32 \
    --output models/saved_models/activity_classifier.h5

# Convert to TensorFlow Lite with quantization
python src/deployment/convert_to_tflite.py \
    --model models/saved_models/activity_classifier.h5 \
    --output models/tflite/activity_classifier.tflite \
    --quantize INT8

# Validate TFLite model accuracy
python src/evaluation/validate_tflite.py \
    --model models/tflite/activity_classifier.tflite \
    --test-data data/processed/test_activity.csv
```

### 3.2 Train LSTM Anomaly Detector

```bash
# Train LSTM Autoencoder for anomaly detection
python src/models/train_lstm_autoencoder.py \
    --data data/processed/health_metrics.csv \
    --sequence-length 50 \
    --epochs 100 \
    --output models/saved_models/lstm_anomaly.h5

# Convert to TFLite (lightweight version for edge)
python src/deployment/convert_to_tflite.py \
    --model models/saved_models/lstm_anomaly.h5 \
    --output models/tflite/anomaly_detector.tflite \
    --quantize INT8 \
    --optimize-for-edge
```

### 3.3 Deploy Models to Wear OS

```bash
# Copy TFLite models to Wear OS assets
cp models/tflite/activity_classifier.tflite ../WearOSApp/app/src/main/assets/
cp models/tflite/anomaly_detector.tflite ../WearOSApp/app/src/main/assets/

# Rebuild Wear OS app with new models
cd ../WearOSApp
./gradlew assembleDebug
```

### 3.4 Setup Cloud ML Training Pipeline (AWS SageMaker)

```bash
# Deploy advanced cloud models
python src/deployment/deploy_to_sagemaker.py \
    --model-type lstm_autoencoder \
    --instance-type ml.p3.2xlarge

# Setup automated retraining
python src/deployment/setup_training_pipeline.py \
    --schedule "cron(0 0 ? * SUN *)"  # Weekly on Sunday
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

## Phase 4: React Native Mobile Dashboard

### 4.1 Setup React Native Project

```bash
cd MobileDashboard_RN

# Install dependencies
npm install
# or
yarn install
```

### 4.2 Configure API Endpoint

Edit `src/config/api.config.ts`:
```typescript
export const API_CONFIG = {
  BASE_URL: 'https://your-api-gateway-url.amazonaws.com/prod',
  TIMEOUT: 10000,
  HEADERS: {
    'Content-Type': 'application/json',
  },
};
```

### 4.3 Setup Expo Notifications

Notifications are already configured with Expo Notifications. To customize:

Edit `src/services/notification.service.ts`:
```typescript
// Configure notification channels and handlers
// Already implemented in the project
```

### 4.4 Run Dashboard

```bash
# Start Expo development server
npm start
# or
yarn start

# Run on specific platform
npm run ios      # iOS (requires macOS)
npm run android  # Android
npm run web      # Web browser

# Or scan QR code with Expo Go app on your phone
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
- [React Native Documentation](https://reactnative.dev/docs/getting-started)
- [Expo Documentation](https://docs.expo.dev/)
- [Zustand State Management](https://github.com/pmndrs/zustand)
