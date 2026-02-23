# Wear OS Health Monitor App

## Overview
Standalone Wear OS application that continuously monitors vital signs and syncs data to the cloud.

## Features
- Real-time heart rate monitoring
- Step counting and calorie tracking
- Local data buffering with Room database
- Background synchronization with cloud backend
- Battery-optimized sensor polling

## Setup Instructions

### 1. Import Project in Android Studio
1. Open Android Studio
2. File → New → Import Project
3. Select this directory (WearOSApp)
4. Wait for Gradle sync

### 2. Configure API Endpoint
Edit `app/src/main/java/com/capstone/healthmonitor/wear/data/network/ApiConfig.kt`:
```kotlin
object ApiConfig {
    const val BASE_URL = "YOUR_CLOUD_API_ENDPOINT"
    const val API_KEY = "YOUR_API_KEY"
}
```

### 3. Build and Run
1. Start Wear OS emulator
2. Click Run → Run 'app'
3. Grant permissions when prompted

## Project Structure

```
app/
├── src/main/
│   ├── java/com/capstone/healthmonitor/wear/
│   │   ├── data/
│   │   │   ├── local/         # Room database
│   │   │   ├── network/       # Retrofit API
│   │   │   └── repository/    # Data repository
│   │   ├── domain/
│   │   │   ├── model/         # Data models
│   │   │   └── usecase/       # Business logic
│   │   ├── presentation/
│   │   │   ├── ui/            # Compose UI
│   │   │   └── viewmodel/     # ViewModels
│   │   ├── service/
│   │   │   ├── HealthService.kt    # Foreground service
│   │   │   └── SyncWorker.kt       # WorkManager sync
│   │   └── di/                # Hilt modules
│   ├── res/                   # Resources
│   └── AndroidManifest.xml
└── build.gradle.kts
```

## Key Components

### HealthMonitoringService
Foreground service that continuously monitors vital signs using Health Services PassiveMonitoringClient (24/7 background collection).

### EdgeMlEngine
On-device ML inference engine with TFLite models + heuristic fallback:

| Model | Task | Accuracy | Size | Latency |
|-------|------|:--------:|:----:|:-------:|
| Activity Classifier | 6-class activity | 34.3% (edge) | ~15KB | <5ms |
| Anomaly LSTM | Reconstruction error | Partial | ~50KB | ~20ms |
| Heuristic Fallback | Rule-based detection | ~75% | — | <1ms |

> **Note**: Cloud models are significantly more accurate (Random Forest F1=1.00 for anomaly, Extra Trees 86.2% for activity). Edge models serve as a privacy-preserving first pass; cloud inference provides the definitive score.

### Room Database
Local storage for buffering health metrics before cloud sync. Offline-first architecture.

### DataSyncWorker
WorkManager worker that periodically syncs buffered data to cloud backend (every 15-60 minutes).

## Testing with Emulator

### Generate Synthetic Data
1. Launch Wear OS emulator
2. Extended Controls (...) → Virtual Sensors
3. Navigate to Health Services tab
4. Adjust values:
   - Heart Rate: 60-180 BPM
   - Steps: 0-10000
   - Calories: 0-3000

### Simulate Anomaly
Set Heart Rate to 155 BPM and maintain for 10 minutes to trigger anomaly detection.

## Permissions Required

```xml
<uses-permission android:name="android.permission.BODY_SENSORS" />
<uses-permission android:name="android.permission.ACTIVITY_RECOGNITION" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
```

## Battery Optimization

- Sensor polling every 5 seconds (configurable)
- Data buffering to reduce network calls
- Background sync every 1-2 minutes
- WorkManager for efficient scheduling

## Troubleshooting

**Issue**: Health Services not available
- Ensure emulator API level is 30+
- Check Health Services dependency version

**Issue**: Network sync failing
- Verify API endpoint configuration
- Check internet permission
- Review cloud backend logs

## Next Steps
1. Complete cloud backend setup
2. Configure API endpoint in ApiConfig.kt
3. Test end-to-end data flow
4. Optimize battery usage based on testing
