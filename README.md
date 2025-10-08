# Real-Time Health Monitoring System

A comprehensive health monitoring solution using Wear OS, AI/ML anomaly detection, and cloud backend.

## Project Overview

This system continuously monitors vital signs from a Wear OS smartwatch, analyzes the data in real-time using ML models in the cloud, and alerts users of any detected anomalies.

## Architecture

```
Wear OS App → Cloud Backend (API Gateway) → ML Pipeline → Mobile Dashboard
     ↓              ↓                          ↓              ↓
  Sensors      Data Storage            Anomaly Detection   Alerts
```

## Project Structure

```
CAP_STONE/
├── WearOSApp/              # Android Wear OS application
├── CloudBackend/           # Cloud functions and APIs
├── MLPipeline/             # Machine Learning models and preprocessing
├── MobileDashboard/        # Flutter mobile app for visualization
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

## Features

- ✅ Real-time vital signs monitoring (Heart Rate, Steps, Calories)
- ✅ Local data buffering with Room database
- ✅ Secure cloud synchronization
- ✅ AI/ML-based anomaly detection (LSTM Autoencoder)
- ✅ Push notifications for anomalies
- ✅ Interactive dashboard for data visualization
- ✅ Historical trend analysis

## Tech Stack

### Wear OS App
- **Language**: Kotlin
- **Framework**: Jetpack Compose for Wear OS
- **Key Libraries**: 
  - Health Services API
  - Room Persistence
  - Retrofit
  - Hilt (Dependency Injection)
  - WorkManager

### Cloud Backend
- **Platform**: AWS (API Gateway + Lambda + DynamoDB)
- **Alternative**: Google Cloud (Cloud Functions + Firestore)
- **Language**: Python/Node.js

### ML Pipeline
- **Language**: Python
- **Libraries**: TensorFlow/Keras, Scikit-learn, Pandas, NumPy
- **Models**: LSTM Autoencoder, Isolation Forest

### Mobile Dashboard
- **Framework**: Flutter
- **State Management**: Provider/Riverpod
- **Features**: Real-time charts, push notifications

## Getting Started

### Prerequisites

- Android Studio (latest version)
- Wear OS SDK (API 30+)
- Python 3.8+
- Flutter SDK
- AWS/GCP Account
- Node.js (for cloud functions)

### Phase 1: Setup Wear OS App

See [WearOSApp/README.md](WearOSApp/README.md) for detailed instructions.

### Phase 2: Setup Cloud Backend

See [CloudBackend/README.md](CloudBackend/README.md) for detailed instructions.

### Phase 3: Setup ML Pipeline

See [MLPipeline/README.md](MLPipeline/README.md) for detailed instructions.

### Phase 4: Setup Mobile Dashboard

See [MobileDashboard/README.md](MobileDashboard/README.md) for detailed instructions.

## Development Phases

1. **Phase 1**: Wear OS data acquisition and permissions
2. **Phase 2**: Cloud synchronization and storage
3. **Phase 3**: ML anomaly detection implementation
4. **Phase 4**: Dashboard and alerting system

## Contributing

This is a capstone project. For contributions, please follow the standard Git workflow.

## License

MIT License

## Contact

For questions or support, please open an issue in the repository.
