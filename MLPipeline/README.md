# ML Pipeline for Health Anomaly Detection

## Overview
Machine learning pipeline for detecting anomalies in health monitoring data and classifying user activities. The pipeline supports both **edge deployment** (TFLite on Wear OS) and **cloud deployment** (scikit-learn on AWS Lambda).

## Models

### 🏆 Best Anomaly Detection Model: Random Forest Classifier

After comprehensive evaluation of 7 different models, **Random Forest** achieved the highest accuracy for health anomaly detection.

| Rank | Model | F1-Score | AUC-ROC | Precision | Recall | Type |
|:----:|-------|:--------:|:-------:|:---------:|:------:|------|
| 👑 | **Random Forest** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | Supervised |
| #2 | Gradient Boosting | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Supervised |
| #3 | Extra Trees | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Supervised |
| #4 | XGBoost | 0.9883 | 1.0000 | 0.9900 | 0.9867 | Supervised |
| #5 | Isolation Forest | 0.8874 | 0.9955 | 0.9367 | 0.8430 | Unsupervised |
| #6 | One-Class SVM | 0.7221 | 0.8528 | 0.7622 | 0.6860 | Unsupervised |
| #7 | Local Outlier Factor | 0.2053 | 0.4732 | 0.2167 | 0.1950 | Unsupervised |

**Cross-Validation**: Random Forest F1 = 1.0000 ± 0.0000 (5-fold CV)

### 🏆 Best Activity Classifier: Extra Trees Classifier

For 6-class activity recognition (sleep, rest, walk, run, exercise, other), **Extra Trees** achieved the highest accuracy.

| Rank | Model | Accuracy | Training Time |
|:----:|-------|:--------:|:------------:|
| 👑 | **Extra Trees** | **86.20%** | 290ms |
| #2 | XGBoost | 85.58% | 1,679ms |
| #3 | Random Forest | 85.42% | 748ms |
| #4 | Gradient Boosting | 85.16% | 26,320ms |
| #5 | TFLite Neural Network (current) | 34.27% | — |

**Extra Trees per-class performance:**

| Activity | F1-Score | Status |
|----------|:--------:|:------:|
| sleep | 0.9247 | ✅ |
| rest | 0.9153 | ✅ |
| walk | 0.8945 | ✅ |
| other | 0.8337 | ✅ |
| run | 0.8064 | ✅ |
| exercise | 0.7935 | ✅ |

### Edge Models (TFLite — On-Device)
- **Activity Classifier**: Dense NN (4 inputs → 32 → 32 → 6 outputs), ~15KB
- **Anomaly Detector**: Conv1D-based autoencoder (seq_len=10, feat_dim=4), ~50KB

### Cloud Models (scikit-learn — AWS Lambda)
- **Random Forest Classifier**: Best anomaly detection model (F1=1.00)
- **Extra Trees Classifier**: Best activity classification model (Acc=86.2%)

## Architecture

```
Raw Data → Preprocessing → Feature Engineering → Model Training
                                                       ↓
Alert ← Anomaly Detection ← Real-time Inference ← Trained Model

Features: heartRate, steps, calories, distance
```

## Directory Structure

```
MLPipeline/
├── data/
│   ├── raw/                    # Raw health metrics
│   ├── processed/              # Cleaned and preprocessed data
│   └── synthetic/              # Synthetic data for testing
├── models/
│   ├── saved_models/           # Trained model artifacts
│   │   ├── isolation_forest.pkl        # Retrained Isolation Forest
│   │   ├── scaler.pkl                  # StandardScaler
│   │   ├── best_anomaly_randomforest.pkl   # 🏆 Best anomaly model
│   │   ├── best_anomaly_scaler.pkl     # Scaler for best anomaly model
│   │   ├── best_activity_extratrees.pkl    # 🏆 Best activity model
│   │   └── best_activity_scaler.pkl    # Scaler for best activity model
│   ├── lambda_export/          # Lambda deployment package
│   ├── tflite/                 # TFLite edge models
│   └── checkpoints/            # Training checkpoints
├── src/
│   ├── data/                   # Data generation
│   ├── preprocessing/          # Data cleaning and preprocessing
│   ├── models/                 # Model training scripts
│   └── tests/                  # Test suites
│       ├── comprehensive_ml_test.py    # 🔬 Full evaluation suite
│       ├── test_sklearn_models.py      # sklearn model tests
│       ├── tflite_smoketest.py         # TFLite model tests
│       ├── test_integration.py         # Integration tests
│       └── run_all_tests.py            # Test orchestrator
└── test_results_comprehensive.json     # Latest test results
```

## Setup

### 1. Create Virtual Environment

```bash
cd MLPipeline
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install numpy pandas scikit-learn xgboost joblib matplotlib tqdm
# Optional: pip install tensorflow  (for TFLite models)
```

### 3. Generate Synthetic Data

```bash
python src/data/generate_synthetic_data.py
```

## Usage

### Run Comprehensive Model Tests

```bash
python src/tests/comprehensive_ml_test.py --output test_results_comprehensive.json
```

This runs 7 test suites:
1. Existing model evaluation (before retrain)
2. Retrained Isolation Forest with proper scaler
3. Unsupervised model comparison (IF vs SVM vs LOF)
4. **Supervised model comparison** (Random Forest vs Gradient Boosting vs Extra Trees vs XGBoost)
5. **Activity classifier comparison** (sklearn alternatives vs TFLite)
6. TFLite activity classifier evaluation
7. TFLite Conv1D autoencoder evaluation

### Train Anomaly Detection Model (Recommended: Random Forest)

```bash
# The comprehensive test script automatically trains and saves the best model
python src/tests/comprehensive_ml_test.py

# Best model saved to: models/saved_models/best_anomaly_randomforest.pkl
# Scaler saved to: models/saved_models/best_anomaly_scaler.pkl
```

### Train Isolation Forest (Legacy/Sklearn Pipeline)

```bash
bash train_pipeline_sklearn.sh
```

### Train LSTM Autoencoder (Deep Learning)

```bash
bash train_pipeline.sh
```

## Model Performance (Tested Feb 2026)

### Anomaly Detection (6,000 samples, 5-fold CV)

| Model | Precision | Recall | F1-Score | AUC-ROC | Latency |
|-------|:---------:|:------:|:--------:|:-------:|:-------:|
| **Random Forest** 🏆 | **1.0000** | **1.0000** | **1.0000** | **1.0000** | ~5ms |
| Gradient Boosting | 1.0000 | 1.0000 | 1.0000 | 1.0000 | ~6ms |
| Extra Trees | 1.0000 | 1.0000 | 1.0000 | 1.0000 | ~3ms |
| XGBoost | 0.9900 | 0.9867 | 0.9883 | 1.0000 | ~3ms |
| Isolation Forest (retrained) | 0.9367 | 0.8430 | 0.8874 | 0.9955 | ~5ms |

### Activity Classification (18,000 samples, 25% test split)

| Model | Accuracy | Training Time |
|-------|:--------:|:------------:|
| **Extra Trees** 🏆 | **86.20%** | 290ms |
| XGBoost | 85.58% | 1,679ms |
| Random Forest | 85.42% | 748ms |
| Gradient Boosting | 85.16% | 26,320ms |

## Deployment

### Deploy Best Model to Lambda

```bash
# The best Random Forest model is already saved for Lambda
# Copy to Lambda export directory:
cp models/saved_models/best_anomaly_randomforest.pkl models/lambda_export/model.pkl
cp models/saved_models/best_anomaly_scaler.pkl models/lambda_export/scaler.pkl

# Upload to S3
aws s3 cp models/lambda_export/ s3://health-ml-models/randomforest/ --recursive
```

### Build TFLite Edge Models

```bash
bash build_edge_models.sh
# Models copied to WearOSApp/app/src/main/assets/models/
```

## Troubleshooting

**Issue**: Isolation Forest classifies everything as anomaly
- The scaler must be applied before prediction
- Use `best_anomaly_randomforest.pkl` instead (F1=1.00)

**Issue**: TFLite activity classifier misclassifies activities
- The Normalization layer was not adapted — call `model.layers[1].adapt(x)` before training
- Use `best_activity_extratrees.pkl` for cloud inference (86.2% accuracy)

**Issue**: Conv1D autoencoder cannot detect bradycardia
- Train only on normal data (current model mixes normal + anomalous)
- Bradycardia MSE (6.63) is lower than normal MSE (19.56)

## Next Steps

1. Deploy Random Forest model to Lambda (replace Isolation Forest)
2. Retrain TFLite models with adapted Normalization layer
3. Collect real-world sensor data from Wear OS devices
4. Add SpO2 and skin temperature features
5. Implement periodic retraining pipeline
6. Add SHAP explainability for anomaly predictions
