# Real-Time Health Monitoring System

**A Hybrid Edge-Cloud Health Monitoring Solution** featuring continuous background health monitoring with on-device ML models for instant privacy-preserving insights, enhanced by serverless cloud-based inference for anomaly detection.

## 🎯 Project Overview

This system continuously monitors vital signs from a Wear OS smartwatch using a **hybrid architecture**:
- 🎯 **Edge-first**: On-device TensorFlow Lite models provide instant activity classification and anomaly detection
- 🧠 **ML-powered**: Lightweight neural networks (Activity Classifier + LSTM Autoencoder) running on-watch
- ☁️ **Cloud-enhanced**: Lambda containerized inference with GradientBoosting (F1=0.995)
- � **Explainable**: Human-readable anomaly reasons from both edge and cloud models
- �🔄 **Continuous monitoring**: Background service runs 24/7 using Wear OS PassiveMonitoringClient
- 🔒 **Privacy-preserving**: Primary detection on-device, only aggregated metrics sent to cloud

## 🌟 Key Features

### ✅ Continuous Background Monitoring
- **24/7 data collection** even when watch screen is off or app is closed
- **PassiveMonitoringClient** for battery-efficient passive health data capture
- **Auto-starts** on device boot and app launch
- **Foreground service** ensures monitoring isn't killed by system

### ✅ Hybrid Edge-Cloud ML
- **Edge TFLite Models** (on-device):
  - Activity Classifier: Dense NN (Input(4) → Normalization → Dense(32) → Dense(32) → Softmax(6)), ~5KB, <5ms inference
    - Classifies activities: sleep, rest, walk, run, exercise, other
    - Input: `[heartRate, steps, calories, distance]`
    - Edge accuracy: 34.3% (cloud XGBoost achieves 85.8%); heuristic fallback when TFLite unavailable
  - LSTM Anomaly Detector: Conv1D autoencoder (seq_len=10, feat_dim=4), ~16KB, ~20ms inference
  - Total edge inference: <25ms, Size: ~21KB total
  
- **Cloud Lambda Inference**:
  - GradientBoosting model (scikit-learn, F1=0.995) — best anomaly detection
  - XGBoost activity classifier (Accuracy=85.8%) — best activity classification
  - Containerized Lambda function (1024MB)
  - Models stored in S3, loaded on-demand
  - Real-time anomaly scoring with overfitting-proof regularization
  - **Anomaly explainability**: Returns human-readable reasons + per-feature contribution percentages

### ✅ Intelligent Data Sync
- **Periodic sync** every 15-60 minutes (configurable)
- **Batched uploads** to minimize network usage
- **WorkManager** for reliable background sync
- **Retry logic** with exponential backoff
- Tracks sync status per metric

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  WEAR OS WATCH (Edge Layer)                         │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ HealthMonitoringService (Foreground Service - 24/7)          │ │
│  │  - PassiveMonitoringClient (continuous background collection)│ │
│  │  - Auto-saves every 30s to Room Database                     │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           ↓                                         │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │ EdgeMlEngine (On-Device Inference)                        │    │
│  │  ┌──────────────────┐  ┌────────────────────────────┐    │    │
│  │  │ Activity         │  │ LSTM Anomaly Detector      │    │    │
│  │  │ Classifier       │  │ (Sequence Reconstruction)  │    │    │
│  │  │ TFLite (~5KB)    │  │ TFLite (~16KB)             │    │    │
│  │  │ <5ms inference   │  │ ~20ms inference            │    │    │
│  │  └──────────────────┘  └────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────────────┘    │
│                           ↓                                         │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │ DataSyncWorker (Periodic - every 15-60 min)              │    │
│  │  - Batches unsynced metrics                              │    │
│  │  - Enriches with edge ML results                         │    │
│  │  - HTTP POST with API key auth                           │    │
│  └────────────────────────┬──────────────────────────────────┘    │
└────────────────────────────┼──────────────────────────────────────┘
                             ↓ HTTPS POST
┌─────────────────────────────────────────────────────────────────────┐
│              AWS CLOUD BACKEND (ap-south-2)                         │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ API Gateway (u8tkgz3vsf...amazonaws.com/prod)               │ │
│  │  - /health-data/ingest - /health-data/sync                  │ │
│  │  - /notifications/register                                   │ │
│  │  - API Key Authentication                                    │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           ↓                                         │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ HealthDataIngestion Lambda (Python 3.9, 512MB)             │  │
│  │  1. Validate & store to DynamoDB                           │  │
│  │  2. Invoke inference Lambda if needed                      │  │
│  │  3. Publish alerts to SNS                                  │  │
│  └────────────┬────────────────────────┬──────────────────────┘  │
│               ↓                        ↓                           │
│  ┌────────────────────┐  ┌─────────────────────────────────────┐ │
│  │ DynamoDB Tables    │  │ HealthAnomalyInference Lambda       │ │
│  │  - HealthMetrics   │  │ (Container 1024MB)                  │ │
│  │  - HealthPushTokens│  │  - GradientBoosting (F1=0.995)      │ │
│  │                    │  │  - Loads model from S3              │ │
│  │ S3 Bucket          │  │  - Returns anomaly score + reasons  │ │
│  │  - Model artifacts │  │  - Feature contribution analysis    │ │
│  │    (*.pkl)         │  └─────────────────────────────────────┘ │
│  └────────────────────┘                                           │
│                          ┌─────────────────────────────────────┐ │
│                          │ HealthReadMetrics Lambda            │ │
│                          │  - Query /health/metrics & history  │ │
│                          │  - Returns anomalyReasons to UI     │ │
│                          └──────────────────────────────────────┘ │
│                                       ↓                           │
│                          ┌─────────────────────────────────────┐ │
│                          │ SNS Topic (health-alerts)           │ │
│                          │  → HealthSnsToExpo Lambda           │ │
│                          │  → Expo Push with anomaly reasons   │ │
│                          │  → SMS Alerts                       │ │
│                          └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
                   ┌────────────────────────────────┐
                   │  React Native Mobile Dashboard │
                   │  - Real-time metrics display   │
                   │  - Anomaly explainability      │
                   │  - Push notifications          │
                   │  - Charts & analytics          │
                   └────────────────────────────────┘
```

## 📂 Project Structure

```
CAP_STONE/
├── WearOSApp/                    # Wear OS smartwatch application
│   ├── app/src/main/
│   │   ├── java/.../
│   │   │   ├── data/            # Repository, DAO, API
│   │   │   ├── domain/          # ML Engine, Use Cases
│   │   │   ├── service/         # Background Service
│   │   │   └── presentation/    # UI (Jetpack Compose)
│   │   └── assets/models/       # TFLite models (*.tflite)
│   └── build.gradle.kts
│
├── CloudBackend/                 # AWS serverless backend
│   └── aws-lambda/
│       ├── deploy.sh            # One-click deployment script
│       ├── destroy.sh           # Tear down all resources
│       ├── lambda_function.py   # Data ingestion Lambda
│       ├── lambda_inference_sklearn.py  # Anomaly inference
│       ├── lambda_read_metrics.py       # Read metrics from DynamoDB
│       ├── sns_to_expo.py       # Push notification handler
│       ├── Dockerfile.inference # Container for ML Lambda
│       └── iam-policy.json      # IAM permissions
│
├── MLPipeline/                   # Machine learning training
│   ├── train_pipeline_sklearn.sh # sklearn training pipeline
│   ├── train_pipeline.sh       # LSTM training pipeline
│   ├── build_edge_models.sh    # Build TFLite models
│   ├── export_for_lambda.sh    # Export LSTM models for Lambda
│   ├── src/
│   │   ├── data/               # Synthetic data generation
│   │   ├── preprocessing/      # Data cleaning & feature engineering
│   │   ├── models/             # Training scripts
│   │   │   ├── train_activity_tflite.py
│   │   │   ├── train_lstm_tflite.py
│   │   │   ├── train_lstm_autoencoder.py
│   │   │   ├── lambda_inference_sklearn.py
│   │   │   └── lambda_inference.py
│   │   └── tests/              # Test suites
│   └── models/
│       ├── tflite/             # Edge models (~21KB)
│       ├── saved_models/       # Cloud models (.pkl)
│       └── lambda_export/      # Lambda deployment package
│
└── MobileDashboard_RN/          # React Native mobile app
    ├── App.tsx                 # Root component
    ├── src/
    │   ├── screens/            # Home, History, Settings
    │   ├── components/         # MetricCard, AnomalyAlert, ActivityCard, etc.
    │   ├── navigation/         # BottomTabNavigator, RootNavigator
    │   ├── services/           # API, notifications, storage
    │   ├── store/              # Zustand state (health.store.ts)
    │   ├── config/             # api.config.ts, theme.config.ts
    │   ├── types/              # TypeScript type definitions
    │   └── utils/              # Date and number utilities
    └── package.json
```

## 🔍 How It Works

### Data Collection Flow
1. **WearOS Service** starts on boot/app launch
2. **PassiveMonitoringClient** collects HR, steps, calories every 30s
3. **EdgeMlEngine** runs TFLite inference:
   - Activity classification (6 states)
   - Anomaly detection (LSTM reconstruction)
4. **Save to Room DB** with edge ML results
5. **WorkManager** triggers sync every 15-60 minutes
6. **Batch upload** to AWS API Gateway
7. **Lambda** stores to DynamoDB, invokes cloud inference
8. **Cloud inference** returns anomaly score + human-readable reasons
9. **anomalyReasons** stored in DynamoDB alongside the metric
10. **SNS** publishes alerts (with top anomaly reason) to mobile app
11. **Mobile Dashboard** displays anomaly reasons in alert cards and history

### Anomaly Detection Logic
```
Edge Score (TFLite LSTM): MSE reconstruction error → [0, 1]
Cloud Score (GradientBoosting): Supervised probability → [0, 1]

if edgeScore >= 0.5:
    ALERT (edge detected)
elif cloudScore >= 0.5:
    ALERT (cloud detected)
elif heartRate > 140 or heartRate < 40:
    ALERT (rule-based)
```

### Anomaly Explainability
When an anomaly is detected, the system generates **human-readable reasons** explaining *why*:

| Source | Method | Example |
|--------|--------|---------|
| **Edge (TFLite)** | Per-feature reconstruction error | "Heart rate: 180 BPM deviates from expected pattern (72% of anomaly signal)" |
| **Cloud (GradientBoosting)** | Range check + feature importance | "Resting heart rate: 180 BPM is above normal range (50–100 BPM)" |
| **Threshold fallback** | Simple range checks | "Heart rate 35 BPM is dangerously low (normal: 50–100 BPM)" |

Reasons flow end-to-end: stored in DynamoDB → included in SNS push body → displayed on Mobile Dashboard alert cards and history screen.

## 🔧 Configuration

### WearOS App
[ApiConfig.kt](WearOSApp/app/src/main/java/com/capstone/healthmonitor/wear/data/network/ApiConfig.kt):
```kotlin
const val BASE_URL = "https://YOUR-API-ID.execute-api.ap-south-2.amazonaws.com/prod/"
const val API_KEY = "YOUR_API_KEY_HERE"
```

### Mobile Dashboard
[api.config.ts](MobileDashboard_RN/src/config/api.config.ts):
```typescript
export const API_BASE_URL = 'https://YOUR-API-ID.execute-api.ap-south-2.amazonaws.com/prod';
export const API_KEY = 'YOUR_API_KEY_HERE';
```

### Lambda Environment Variables (set by deploy.sh)
- `TABLE_NAME`: HealthMetrics
- `PUSH_TOKEN_TABLE`: HealthPushTokens
- `API_KEY`: Auto-generated API key
- `SNS_TOPIC_ARN`: ARN of health-alerts topic
- `CLOUD_INFERENCE_FUNCTION`: HealthAnomalyInference
- `MODEL_BUCKET`: health-ml-models
- `MODEL_KEY`: gradientboosting/model.pkl
- `SCALER_KEY`: gradientboosting/scaler.pkl

## ⚠️ Troubleshooting

### WearOS App Issues

**Service not starting:**
```bash
# Check permissions
adb shell pm list permissions -g | grep BODY_SENSORS

# Check service status
adb logcat | grep "HealthMonitorService"

# Restart service
adb shell am stopservice com.capstone.healthmonitor.wear/.service.HealthMonitoringService
adb shell am startservice com.capstone.healthmonitor.wear/.service.HealthMonitoringService
```

**TFLite models not loading:**
```bash
# Rebuild models
cd MLPipeline && ./build_edge_models.sh

# Check assets
adb shell ls /data/app/.../assets/models/

# View logs
adb logcat | grep "TfLiteSanityCheck\|EdgeMlEngine"
```

**Sync failing:**
```bash
# Check network
adb shell ping google.com

# Test API endpoint
curl -X POST YOUR_ENDPOINT -H 'X-API-Key: YOUR_KEY' -d '{...}'

# View sync logs
adb logcat | grep "DataSyncWorker\|HealthRepository"
```

### Cloud Backend Issues

**Lambda errors:**
```bash
# Tail logs
aws logs tail /aws/lambda/HealthDataIngestion --region ap-south-2 --follow

# Check function config
aws lambda get-function --function-name HealthDataIngestion --region ap-south-2

# Test directly
aws lambda invoke --function-name HealthDataIngestion --payload '...' out.json --region ap-south-2
```

**API Gateway 403:**
- Ensure `X-API-Key` header is present and correct
- Check API Gateway usage plan association
- Verify Lambda permissions for API Gateway invocation

**Cloud inference returning 400:**
- The inference Lambda supports both API Gateway events (`body` wrapper) and direct invocation (raw payload). If the ingestion Lambda calls inference via `lambda_client.invoke()`, it sends a raw payload — ensure the inference handler parses both formats.

**Cloud inference returning 500 (MT19937 BitGenerator):**
- This is a numpy version mismatch. Models pickled with numpy 2.x cannot be loaded with numpy 1.x. Ensure `requirements-layer.txt` pins `numpy>=2.0.0` and rebuild the container.

**DynamoDB issues:**
```bash
# Check table
aws dynamodb describe-table --table-name HealthMetrics --region ap-south-2

# Query data
aws dynamodb scan --table-name HealthMetrics --limit 5 --region ap-south-2
```

## 🧪 Testing

### Unit Tests
```bash
# WearOS
cd WearOSApp && ./gradlew test

# Lambda (local)
cd CloudBackend/aws-lambda && python -m pytest
```

### Integration Tests
```bash
# Test full pipeline
./test_lambda_handler.sh
```

## 📊 Monitoring

- **CloudWatch Logs**: Lambda execution logs
- **CloudWatch Metrics**: Lambda invocations, errors, duration
- **DynamoDB Metrics**: Read/write capacity, throttling
- **API Gateway Metrics**: Request count, latency, 4xx/5xx errors

## 🤝 Contributing

This is an academic capstone project. For educational purposes only.

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 👤 Author

Ramadugu Dhanush - Capstone Project 2026

## 📧 Contact

For questions or support, please open an issue in the repository.

## ✨ Implemented Features

### 🎯 Continuous Health Monitoring
- ✅ **24/7 background monitoring** - Runs continuously even when screen is off
- ✅ **Passive data collection** - Uses Wear OS PassiveMonitoringClient
- ✅ **Auto-start on boot** - Service starts automatically on device reboot
- ✅ **Battery optimized** - Efficient passive monitoring with minimal battery impact
- ✅ **Real-time metrics** - Heart rate, steps, calories collected every 30s
- ✅ **Local storage** - Room database for offline-first architecture

### 🧠 Hybrid ML Anomaly Detection

**Edge Layer (On-Device TFLite)**:
- ✅ **Activity Classifier** - Dense NN identifying 6 activity states (sleep/rest/walk/run/exercise/other) from `[heartRate, steps, calories, distance]` input; ~5KB, <5ms inference; 34.3% edge accuracy with heuristic fallback
- ✅ **LSTM Anomaly Detector** - Sequence-based anomaly detection using reconstruction error
- ✅ **Instant inference** - <25ms total latency on wearable device
- ✅ **Fallback heuristics** - Rule-based detection if TFLite models unavailable
- ✅ **Model versioning** - Tracks which model version produced each prediction

**Cloud Layer (Lambda Containers)**:
- ✅ **GradientBoosting Classifier** — Best anomaly detection model (F1=0.995, AUC-ROC=1.00) 🏆
- ✅ **XGBoost Classifier** — Best activity classification model (Accuracy=85.8%) 🏆
- ✅ **RandomForest / ExtraTrees** — Backup anomaly models (F1=0.983 / 0.966)
- ✅ **Isolation Forest** — Unsupervised anomaly detection fallback (F1=0.491)
- ✅ **Anomaly explainability** — Human-readable reasons for every anomaly (range checks + feature importance weighting)
- ✅ **Feature contributions** — Per-feature contribution percentages from GradientBoosting feature_importances_
- ✅ **Serverless inference** — Containerized Lambda with 1024MB memory
- ✅ **S3 model storage** — 7 models stored (gradientboosting, randomforest, xgboost, extratrees, isolation_forest, activity)
- ✅ **Hybrid scoring** — Combines edge and cloud anomaly scores
- ✅ **Overfitting-proof** — All supervised models regularized (max_depth=8, min_samples_leaf=5), train-test gap < 0.01

### 📱 Smart Data Synchronization
- ✅ **Periodic sync** - WorkManager schedules sync every 15-60 minutes
- ✅ **Batched uploads** - Sends multiple metrics in single API call
- ✅ **Network constraints** - Only syncs when connected to network
- ✅ **Retry logic** - Exponential backoff on failures
- ✅ **Sync tracking** - Marks metrics as synced in local database
- ✅ **Data cleanup** - Automatic deletion of old synced data (7-30 days)

### 🔔 Intelligent Alerting
- ✅ **SNS topic integration** - Centralized alert distribution
- ✅ **Expo push notifications** - Real-time alerts with anomaly reasons in push body
- ✅ **SMS alerts** - Optional SMS notifications for critical anomalies
- ✅ **Multi-subscriber** - Easy to add webhooks, email, etc.
- ✅ **Haptic feedback** - On-watch vibration for immediate alerts
- ✅ **Contextual alerts** - Push notifications include the top anomaly reason (e.g., "Heart rate 180 BPM is dangerously high")

### 📱 Mobile Dashboard (React Native)
- ✅ **Real-time metrics** — Live display of latest health data
- ✅ **Activity classification** — Shows detected activity (sleep/rest/walk/run/exercise) with icons
- ✅ **Anomaly alerts** — Visual anomaly alert cards with scores and **human-readable reasons**
- ✅ **Anomaly explainability** — Alert cards show why each anomaly occurred (source + reasons)
- ✅ **Historical trends** — Grouped by date with activity + anomaly badges + reason tooltips
- ✅ **Push notifications** — Receives anomaly alerts with contextual explanations
- ✅ **Settings management** — Configure sync interval, notifications
- ✅ **Manual data entry** — Add metrics manually for testing
- ✅ **Offline-first** — AsyncStorage cache with mock data fallback

## 🛠️ Tech Stack

### WearOS App
- **Language**: Kotlin
- **UI**: Jetpack Compose for Wear OS
- **Architecture**: MVVM with Repository pattern
- **Dependency Injection**: Hilt/Dagger
- **Database**: Room (SQLite)
- **Networking**: Retrofit + OkHttp
- **Background Work**: WorkManager
- **Health Data**: Health Services API (PassiveMonitoringClient)
- **ML**: TensorFlow Lite (v2.15)
- **Key Features**:
  - Foreground service for 24/7 monitoring
  - Passive data collection with minimal battery impact
  - On-device ML inference with TFLite
  - Offline-first with periodic cloud sync

### AWS Cloud Backend
- **Region**: ap-south-2 (Hyderabad)
- **API Gateway**: REST API with API key authentication
- **Lambda Functions**:
  - `HealthDataIngestion` (Python 3.9, Zip deployment, 512MB)
  - `HealthAnomalyInference` (Python 3.9, Container image, 1024MB)
  - `HealthReadMetrics` (Python 3.9, Zip deployment, 256MB)
  - `HealthSnsToExpo` (Python 3.9, Zip deployment, 256MB)
- **Database**: DynamoDB (Pay-per-request billing)
  - `HealthMetrics` table (userId + timestamp composite key)
  - `HealthPushTokens` table (userId + deviceId composite key)
- **Storage**: S3 bucket (`health-ml-models`) for ML artifacts
- **Messaging**: SNS topic (`health-alerts`) for multi-channel notifications
- **Container Registry**: ECR for Lambda container images
- **IAM**: Fine-grained permissions for Lambda execution

### ML Pipeline
- **Training Environment**: Local (Python 3.11 with scikit-learn, XGBoost, TensorFlow 2.15)
- **Edge Models** (TFLite):
  - Activity Classifier: Dense NN (4 inputs → 32 → 32 → 6 outputs), ~5KB
  - Anomaly Detector: Conv1D-based autoencoder (seq_len=10, feat_dim=4), ~16KB
  - Total size: ~21KB, Quantized with DEFAULT optimization
- **Cloud Models** (scikit-learn):
  - **GradientBoosting Classifier**: Best anomaly detection (F1=0.995, AUC=1.00) 🏆
  - **XGBoost Classifier**: Best activity classification (Accuracy=85.8%) 🏆
  - RandomForest (F1=0.983), ExtraTrees (F1=0.966) as backups
  - Isolation Forest: Unsupervised anomaly detection fallback (F1=0.491)
  - All supervised models regularized (max_depth=8, min_samples_leaf=5, max_features='sqrt')
  - Train-test F1 gaps all < 0.01 (no overfitting)
  - Serialized with joblib/pickle to S3
- **Deployment**:
  - Edge: Models copied to `WearOSApp/app/src/main/assets/models/`
  - Cloud: Models uploaded to S3, loaded by Lambda at runtime
- **Scripts**:
  - `build_edge_models.sh` - Train and export TFLite models
  - `export_for_lambda.sh` - Export scikit-learn models for Lambda
  - `deploy.sh` - Deploy Lambda functions with dependencies
  - `src/tests/comprehensive_ml_test.py` - Full model evaluation suite

### Mobile Dashboard
- **Framework**: React Native 0.81.5 + Expo SDK 54
- **Language**: TypeScript
- **State Management**: Zustand (lightweight alternative to Redux)
- **Navigation**: React Navigation 7 (Bottom Tabs)
- **Icons**: @expo/vector-icons
- **Animations**: Lottie (lottie-react-native), react-native-reanimated
- **Graphics**: react-native-svg
- **Notifications**: Expo Notifications + expo-device
- **Storage**: @react-native-async-storage/async-storage
- **Networking**: Axios + @react-native-community/netinfo
- **Styling**: StyleSheet with responsive design
- **Platform Support**: iOS and Android

## 🚀 Quick Start

### Prerequisites

- **Android Studio**: Hedgehog or later (for WearOS app)
- **Python**: 3.11+ (for ML training)
- **Node.js**: 18+ (for React Native dashboard)
- **Expo CLI**: `npm install -g expo-cli`
- **AWS CLI**: Configured with credentials
- **Docker**: For building Lambda container images
- **Physical Wear OS watch** or emulator (API 30+)

### 1️⃣ Deploy Cloud Backend

```bash
cd CloudBackend/aws-lambda

# Deploy entire stack (API Gateway + Lambda + DynamoDB + S3 + SNS)
./deploy.sh

# Note the outputs:
# - API Endpoint: https://u8tkgz3vsf.execute-api.ap-south-2.amazonaws.com/prod/health-data/ingest
# - API Key: [Your API Key]
```

### 2️⃣ Build Edge ML Models (Optional)

```bash
cd MLPipeline

# Build TFLite models for WearOS
./build_edge_models.sh

# Models are automatically copied to WearOSApp/app/src/main/assets/models/
```

### 3️⃣ Setup WearOS App

```bash
cd WearOSApp

# Update API configuration
# Edit: app/src/main/java/com/capstone/healthmonitor/wear/data/network/ApiConfig.kt
# Set: BASE_URL and API_KEY from deploy.sh output

# Build and install
./gradlew installDebug

# Or open in Android Studio and run
```

### 4️⃣ Setup Mobile Dashboard

```bash
cd MobileDashboard_RN

# Install dependencies
npm install

# Update API configuration
# Edit: src/config/api.config.ts
# Set: API_BASE_URL and API_KEY

# Start development server
npx expo start

# Press 'a' for Android or 'i' for iOS
```

### 5️⃣ Test End-to-End

1. **Start WearOS app** - Service should auto-start on launch
2. **Check logs**: `adb logcat | grep HealthMonitor`
   - Should see "Background Monitoring" active
   - Should see "TFLite sanity checks complete"
3. **Wait for data collection** (~30 seconds)
4. **Trigger manual sync**: Settings → Apply (with sync interval)
5. **Check mobile dashboard** - Should display synced metrics
6. **Test cloud API**:
   ```bash
   curl -X POST https://your-api-endpoint/health-data/ingest \
     -H 'Content-Type: application/json' \
     -H 'X-API-Key: YOUR_API_KEY' \
     -d '{ "userId": "test", "timestamp": 1708300800000, "deviceId": "test-device", "metrics": {"heartRate": 75, "steps": 5000} }'
   ```

## 📚 Detailed Documentation

- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - Complete system architecture and data flow
- **[QUICK_START.md](QUICK_START.md)** - Step-by-step setup guide
- **[PROJECT_SETUP_GUIDE.md](PROJECT_SETUP_GUIDE.md)** - Development environment setup
- **[WearOSApp/README.md](WearOSApp/README.md)** - WearOS app details
- **[CloudBackend/README.md](CloudBackend/README.md)** - AWS backend deployment
- **[MLPipeline/README.md](MLPipeline/README.md)** - ML model training and deployment
- **[MobileDashboard_RN/README.md](MobileDashboard_RN/README.md)** - React Native dashboard

## 📊 Project Status

### ✅ Completed
- [x] WearOS continuous background monitoring with PassiveMonitoringClient
- [x] Edge TFLite models integrated and working (Activity + Anomaly)
- [x] AWS Lambda serverless backend deployed
- [x] DynamoDB storage with efficient schema
- [x] API Gateway with API key authentication
- [x] SNS notifications with Expo push integration
- [x] React Native mobile dashboard
- [x] Hybrid edge-cloud anomaly detection
- [x] Anomaly explainability — human-readable reasons from edge and cloud
- [x] Feature contribution analysis — per-feature anomaly contributions
- [x] Contextual push notifications — anomaly reasons in push body
- [x] Smart data sync with WorkManager
- [x] Auto-start service on boot

### 🚧 Future Enhancements
- [ ] Model retraining pipeline (periodic updates)
- [ ] A/B testing for model versions
- [ ] Federated learning implementation
- [ ] Advanced analytics dashboard
- [ ] Multi-user support with authentication
- [ ] Historical trend prediction
- [ ] Integration with health APIs (Google Fit, Apple Health)

## Contributing

This is a capstone project. For contributions, please follow the standard Git workflow.

## License

MIT License

## Contact

For questions or support, please open an issue in the repository.
