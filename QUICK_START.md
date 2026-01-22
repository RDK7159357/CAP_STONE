# 🚀 Quick Start Guide - Real-Time Health Monitoring System

This guide will help you get started quickly with the Real-Time Health Monitoring System.

## Prerequisites Checklist

- [ ] **Android Studio** (latest version) - [Download](https://developer.android.com/studio)
- [ ] **Python 3.8+** - Check: `python3 --version`
- [ ] **AWS Account** (or Google Cloud) - [AWS Sign up](https://aws.amazon.com/)
- [ ] **Node.js 16+** and npm/yarn - Check: `node --version`
- [ ] **Expo CLI** - Install: `npm install -g expo-cli`
- [ ] **Git** - Check: `git --version`

## 🎯 Option 1: Fast Track (Testing Only - 30 minutes)

Perfect for quick demo/testing without cloud deployment.

### Step 1: Setup Wear OS Emulator (10 min)

```bash
# Open Android Studio
# Tools → Device Manager → Create Device → Wear OS
# Select: Wear OS Small Round (API 30+)
# Launch the emulator
```
[]
### Step 2: Run Wear OS App (5 min)

```bash
cd CAP_STONE/WearOSApp

# Open in Android Studio
# File → Open → Select WearOSApp folder

# In ApiConfig.kt, temporarily use mock endpoint:
# const val BASE_URL = "http://10.0.2.2:8000/"  // Local test server

# Click Run (Shift + F10)
# Grant permissions when prompted
```

### Step 3: Generate Test Data (5 min)

In Wear OS Emulator:
1. Extended Controls (...) → Virtual Sensors → Health Services
2. Set Heart Rate: 155 BPM (high - triggers anomaly)
3. Set Steps: 5000
4. Watch the app receive data

### Step 4: Train ML Model with Synthetic Data (10 min)

```bash
cd CAP_STONE/MLPipeline

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# or: .\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Generate synthetic data
python src/data/generate_synthetic_data.py

# Train model
python src/models/train_lstm_autoencoder.py \
    --data data/processed/health_metrics.csv \
    --epochs 20 \
    --batch-size 32
```

✅ **You're done!** You now have a working Wear OS app collecting data and a trained ML model.

---

## 🏗️ Option 2: Full Production Setup (2-3 hours)

Complete end-to-end setup with cloud backend and mobile dashboard.

### Phase 1: Cloud Backend Deployment (45 min)

#### Using AWS (Recommended)

```bash
cd CAP_STONE/CloudBackend/aws-lambda

# Configure AWS CLI
aws configure
# Enter your: Access Key ID, Secret Access Key, Region (us-east-1)

# Make deployment script executable
chmod +x deploy.sh

# Deploy everything
./deploy.sh
```

**Copy the API endpoint URL from output!** You'll need it for the next steps.

Example output:
```
📍 API Endpoint: https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/health-data/ingest
```

#### Manual Deployment (If script fails)

```bash
# 1. Create DynamoDB Table
aws dynamodb create-table \
    --table-name HealthMetrics \
    --attribute-definitions AttributeName=userId,AttributeType=S AttributeName=timestamp,AttributeType=N \
    --key-schema AttributeName=userId,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST

# 2. Create Lambda Function
pip install -r requirements.txt -t .
zip -r function.zip .
aws lambda create-function \
    --function-name HealthDataIngestion \
    --runtime python3.9 \
    --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip

# 3. Create API Gateway (use AWS Console - easier)
# Visit: https://console.aws.amazon.com/apigateway
```

### Phase 2: Update Wear OS App (10 min)

```bash
cd CAP_STONE/WearOSApp/app/src/main/java/com/capstone/healthmonitor/wear/data/network

# Edit ApiConfig.kt
```

Replace:
```kotlin
const val BASE_URL = "https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/"
const val API_KEY = "your-api-key"  // If you set up API key authentication
```

**Rebuild and run the app:**
```bash
# In Android Studio: Build → Clean Project → Rebuild Project
# Run the app on Wear OS emulator
```

### Phase 3: ML Pipeline Setup (30 min)

```bash
cd CAP_STONE/MLPipeline

# Activate virtual environment
source venv/bin/activate

# Generate training data (if not done already)
python src/data/generate_synthetic_data.py

# Train production model
python src/models/train_lstm_autoencoder.py \
    --data data/processed/health_metrics.csv \
    --epochs 100 \
    --batch-size 32 \
    --output models/saved_models/lstm_autoencoder.h5

# Deploy to AWS SageMaker (optional)
python src/deployment/deploy_to_sagemaker.py
```

### Phase 4: Mobile Dashboard (30 min)

```bash
cd CAP_STONE/MobileDashboard_RN

# Install dependencies
npm install
# or
yarn install

# Update API endpoint in src/config/api.config.ts
# Replace BASE_URL with your API Gateway URL
export const API_CONFIG = {
  BASE_URL: 'https://your-api-gateway-url.com',
  // ...
};

# Start Expo development server
npm start
# or
yarn start

# Run on device/emulator
# iOS: npm run ios (requires macOS and Xcode)
# Android: npm run android
# Or scan QR code with Expo Go app on physical device
```

---

## 🧪 Testing the Complete System

### End-to-End Test Scenario

1. **Start Wear OS App**
   - Launch app on emulator
   - Grant permissions
   - Verify "Monitoring Active" message

2. **Simulate Anomaly**
   ```
   Emulator → Extended Controls → Virtual Sensors → Health Services
   Set Heart Rate: 165 BPM (keep for 2-3 minutes)
   ```

3. **Verify Data Flow**
   ```bash
   # Check CloudWatch Logs (AWS)
   aws logs tail /aws/lambda/HealthDataIngestion --follow
   
   # Check DynamoDB
   aws dynamodb scan --table-name HealthMetrics --limit 5
   ```

4. **Check ML Detection**
   ```bash
   cd MLPipeline
   python src/inference/realtime_detector.py \
       --model models/saved_models/lstm_autoencoder.h5
   ```

5. **Verify Mobile Alert**
   - Open mobile dashboard
   - Check for anomaly notification
   - View in alerts/history section

---

## 📊 Project Status Dashboard

Track your progress:

```
Phase 1: Wear OS Data Collection
├── [✓] Android Studio installed
├── [✓] Wear OS emulator created
├── [✓] App permissions configured
├── [✓] Health Services API integrated
└── [✓] Local database working

Phase 2: Cloud Backend
├── [✓] AWS account setup
├── [✓] DynamoDB table created
├── [✓] Lambda function deployed
├── [✓] API Gateway configured
└── [✓] Tested with Postman

Phase 3: ML Pipeline
├── [✓] Python environment setup
├── [✓] Synthetic data generated
├── [✓] Baseline model trained
├── [✓] LSTM Autoencoder trained
└── [✓] Model evaluation complete

Phase 4: Mobile Dashboard
├── [✓] Node.js and npm installed
├── [✓] Expo CLI installed
├── [✓] Dependencies installed
├── [✓] Dashboard UI created
├── [✓] Push notifications working
└── [✓] Charts displaying data

Integration Testing
├── [✓] Wear OS → Cloud sync verified
├── [✓] Cloud → ML pipeline working
├── [✓] Anomaly detection functional
├── [✓] Mobile alerts received
└── [✓] End-to-end test passed
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Wear OS App - "Health Services not available"
```bash
# Solution:
# Ensure emulator API level is 30+
# Update Health Services dependency in build.gradle
implementation("androidx.health:health-services-client:1.0.0-rc02")
```

### Issue 2: AWS Deployment - "Access Denied"
```bash
# Solution:
# Verify AWS credentials
aws sts get-caller-identity

# Attach required policies to IAM user
aws iam attach-user-policy \
    --user-name YOUR_USERNAME \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

### Issue 3: Lambda Function - "Module not found"
```bash
# Solution:
# Install dependencies in Lambda package
cd CloudBackend/aws-lambda
pip install -r requirements.txt -t ./package
cd package && zip -r ../function.zip . && cd ..
zip -g function.zip lambda_function.py

# Update function
aws lambda update-function-code \
    --function-name HealthDataIngestion \
    --zip-file fileb://function.zip
```

### Issue 4: React Native - "Metro bundler error"
```bash
# Solution:
# Clear Metro cache and reinstall dependencies
cd MobileDashboard_RN
rm -rf node_modules package-lock.json
npm install
npm start -- --reset-cache
```

### Issue 5: ML Model - "Out of Memory"
```python
# Solution: Reduce batch size and sequence length
python src/models/train_lstm_autoencoder.py \
    --sequence-length 30 \  # Reduced from 60
    --batch-size 16 \       # Reduced from 32
    --epochs 50
```

---

## 📈 Next Steps After Setup

1. **Collect Real Data**
   - Wear the device for 24 hours
   - Collect baseline normal data
   - Include various activities (rest, exercise, sleep)

2. **Retrain Model**
   - Use real data instead of synthetic
   - Adjust anomaly threshold based on your patterns
   - Implement online learning

3. **Customize Alerts**
   - Define personalized thresholds
   - Add alert severity levels
   - Implement smart notifications (don't alert during exercise)

4. **Scale the System**
   - Add multiple users support
   - Implement data encryption
   - Add HIPAA compliance features
   - Deploy to production environment

5. **Add Features**
   - Export health reports (PDF)
   - Share data with healthcare providers
   - Add medication tracking
   - Integrate with Apple Health / Google Fit

---

## 🆘 Getting Help

- **Documentation**: See detailed docs in each folder's README.md
- **Issues**: Check `docs/troubleshooting.md`
- **Logs**: 
  - Wear OS: `adb logcat | grep HealthMonitor`
  - AWS: `aws logs tail /aws/lambda/HealthDataIngestion`
  - React Native: Check Metro bundler console or Expo DevTools

---

## 📚 Learning Resources

- [Health Services API Guide](https://developer.android.com/training/wearables/health-services)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [TensorFlow Time Series](https://www.tensorflow.org/tutorials/structured_data/time_series)
- [React Native Documentation](https://reactnative.dev/docs/getting-started)
- [Expo Documentation](https://docs.expo.dev/)
- [Zustand State Management](https://github.com/pmndrs/zustand)

---

**Ready to Start?** Choose your path above and let's build! 🚀
