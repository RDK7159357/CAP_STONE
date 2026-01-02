# Real-Time Health Monitoring System

**A Hybrid Edge-Cloud Health Monitoring Solution** featuring personalized, context-aware anomaly detection with on-device ML models for instant privacy-preserving insights, enhanced by cloud-based deep learning for continuous improvement.

## Project Overview

This system continuously monitors vital signs from a Wear OS smartwatch using a **hybrid architecture**:
- 🎯 **Edge-first**: On-device TensorFlow Lite models provide instant, personalized anomaly detection
- 🧠 **ML-powered**: Lightweight neural networks for context classification and pattern recognition
- ☁️ **Cloud-enhanced**: Advanced deep learning models train in the cloud, deploy to edge devices
- 🔄 **Continuous learning**: Cloud aggregates insights, improves models, pushes updates to devices

## 🌟 Unique Innovation

**Hybrid Edge-Cloud ML with Personalized Context-Awareness**

Unlike traditional health monitors that use either fixed thresholds OR cloud-only ML, our hybrid approach combines:
- ✨ **Personal on-device ML** - TensorFlow Lite models learn YOUR unique patterns locally
- 🏃 **ML-based activity recognition** - Neural network classifies activity states accurately
- 🔒 **Privacy-preserving** - Primary detection on-device, only aggregated insights to cloud
- ⚡ **Instant response** - Edge inference for immediate alerts (< 100ms)
- 🧠 **Cloud intelligence** - LSTM models train on historical data, deploy optimized models to edge
- 🔄 **Federated learning** - Improve models across users without sharing personal data

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  WEAR OS WATCH (Edge Computing)              │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  Sensors   │→ │  TFLite      │→ │  Anomaly Engine   │   │
│  │  (HR, Accel)│  │  Activity    │  │  (Personal Model) │   │
│  └────────────┘  │  Classifier  │  └─────────┬─────────┘   │
│                   └──────────────┘            ↓              │
│  ┌────────────────────────────────────────────────────┐     │
│  │        Instant Alert (< 100ms latency)             │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────────┬─────────────────────────────────┘
                             ↓ (Periodic sync + model updates)
┌──────────────────────────────────────────────────────────────┐
│                    CLOUD BACKEND (ML Pipeline)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  DynamoDB    │→ │  LSTM        │→ │  Model Training  │  │
│  │  (Time-series)│  │  Autoencoder │  │  & Optimization  │  │
│  └──────────────┘  └──────────────┘  └────────┬─────────┘  │
│                                                 ↓             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  TFLite Model Export → Push to Edge Devices         │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │  Dashboard   │  │  Advanced    │                         │
│  │  (Flutter)   │  │  Analytics   │                         │
│  └──────────────┘  └──────────────┘                         │
└──────────────────────────────────────────────────────────────┘
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

### 🎯 Core Innovation (Hybrid Edge-Cloud ML)
- ✅ **On-device TensorFlow Lite models** - Instant inference on smartwatch (< 100ms)
- ✅ **ML-based activity recognition** - Neural network classifies movement patterns
- ✅ **Personalized anomaly detection** - LSTM Autoencoder learns your unique patterns
- ✅ **Federated learning** - Models improve from population without sharing your data
- ✅ **Cloud-trained, edge-deployed** - Best of both worlds
- ✅ **Offline-capable** - Works without internet, syncs when connected

### 🧠 Machine Learning Features
- ✅ **Edge ML**: TFLite activity classifier (6 states: sleep, rest, walk, run, exercise, other)
- ✅ **Edge ML**: Lightweight anomaly detector for instant alerts
- ✅ **Cloud ML**: LSTM Autoencoder for complex pattern recognition
- ✅ **Cloud ML**: Time-series forecasting for predictive alerts
- ✅ **Model versioning**: A/B testing and gradual rollout of improved models
- ✅ **Continuous improvement**: Models retrain weekly on aggregated data

### 📱 Platform Features
- ✅ Real-time vital signs monitoring (Heart Rate, SpO2, Steps, Calories, Movement)
- ✅ 7-day personalized baseline learning (on-device)
- ✅ Local data storage with Room database
- ✅ Smart cloud sync (batched, compression, retry logic)
- ✅ Immediate on-device ML-powered notifications
- ✅ Interactive dashboard with predictive insights
- ✅ Battery-optimized adaptive sampling

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

### ML Pipeline (Hybrid Edge-Cloud)
- **Edge Deployment**: TensorFlow Lite (on Wear OS)
- **Cloud Training**: TensorFlow/Keras, PyTorch
- **Model Optimization**: Quantization, Pruning for edge deployment
- **Libraries**: Scikit-learn, Pandas, NumPy, Optuna
- **Models**: 
  - Edge: TFLite Activity Classifier, Lightweight Anomaly Detector
  - Cloud: LSTM Autoencoder, Attention-based Time Series Models
- **MLOps**: Model versioning, A/B testing, performance monitoring

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
