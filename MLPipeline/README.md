# ML Pipeline for Health Anomaly Detection

## Overview

Machine learning pipeline for detecting anomalies in health monitoring data and classifying user activities. Two deployment targets:

- **Edge (Wear OS)** — TFLite models run on-device for real-time inference
- **Cloud (AWS Lambda)** — scikit-learn models run server-side for higher accuracy

Input features across all models: `heartRate`, `steps`, `calories`, `distance`.

---

## Models

### Anomaly Detection — Best Model: Gradient Boosting

Evaluated on 6,000 synthetic samples (5,000 normal + 1,000 anomalous), 30% test split. Results from `test_results_comprehensive.json` (March 6, 2026):

| Rank | Model | F1-Score | AUC-ROC | Precision | Recall | Training Time | Type |
|:----:|-------|:--------:|:-------:|:---------:|:------:|:------------:|------|
| 1 | **Gradient Boosting** | **0.9950** | **1.0000** | 0.9934 | 0.9967 | 354ms | Supervised |
| 2 | XGBoost | 0.9885 | 0.9999 | 0.9772 | 1.0000 | 118ms | Supervised |
| 3 | Random Forest | 0.9832 | 0.9999 | 0.9899 | 0.9767 | 152ms | Supervised |
| 4 | Extra Trees | 0.9656 | 0.9999 | 0.9965 | 0.9367 | 92ms | Supervised |
| 5 | One-Class SVM | 0.6776 | 0.9043 | 0.7160 | 0.6430 | 563ms | Unsupervised |
| 6 | Isolation Forest | 0.4905 | 0.8477 | 0.5178 | 0.4660 | 282ms | Unsupervised |
| 7 | Local Outlier Factor | 0.1737 | 0.4608 | 0.1833 | 0.1650 | 40ms | Unsupervised |

**Cross-validation (5-fold):** Gradient Boosting F1 = 0.9950 ± 0.0016, AUC = 1.0000 ± 0.0000

The **Gradient Boosting** model is currently deployed to Lambda (`models/lambda_export/model.pkl`).

### Activity Classification — Best Model: XGBoost

6-class classification (sleep, rest, walk, run, exercise, other). Evaluated on 18,000 synthetic samples, 25% test split:

| Rank | Model | Accuracy | Training Time |
|:----:|-------|:--------:|:------------:|
| 1 | **XGBoost** | **85.80%** | 1,220ms |
| 2 | Random Forest | 85.44% | 342ms |
| 3 | Gradient Boosting | 85.40% | 12,990ms |
| 4 | Extra Trees | 84.49% | 162ms |

**XGBoost per-class F1:**

| Activity | F1-Score |
|----------|:--------:|
| sleep | 0.9308 |
| rest | 0.9177 |
| walk | 0.8902 |
| other | 0.8303 |
| run | 0.7899 |
| exercise | 0.7875 |

### Edge Models (TFLite — On-Device)

Built via `build_edge_models.sh` using TensorFlow/Python 3.11, deployed to `WearOSApp/app/src/main/assets/models/`:

| Model | Architecture | Input Shape | Output | Size |
|-------|-------------|:-----------:|--------|:----:|
| Activity Classifier | Dense NN (4→32→32→6 softmax) | `[1, 4]` | 6-class probabilities | ~5 KB |
| Anomaly Detector | Conv1D autoencoder (3 layers) | `[1, 10, 4]` | Reconstructed sequence | ~16 KB |

The activity classifier labels: `sleep`, `rest`, `walk`, `run`, `exercise`, `other`.
The anomaly detector uses reconstruction error — higher MSE indicates anomaly.

### Cloud Models (scikit-learn — AWS Lambda)

| Model | File | Size | Purpose |
|-------|------|:----:|---------|
| Gradient Boosting | `best_anomaly_gradientboosting.pkl` | 228 KB | Anomaly detection (deployed) |
| Random Forest | `best_anomaly_randomforest.pkl` | 456 KB | Anomaly detection (backup) |
| Isolation Forest | `isolation_forest.pkl` | 1.9 MB | Unsupervised fallback |
| XGBoost | `best_activity_xgboost.pkl` | 1.4 MB | Activity classification |
| Extra Trees | `best_activity_extratrees.pkl` | 76.8 MB | Activity classification (backup) |

---

## Directory Structure

```
MLPipeline/
├── src/
│   ├── data/
│   │   └── generate_synthetic_data.py      # Synthetic data generator (normal + anomalous + scenarios)
│   ├── preprocessing/
│   │   └── data_cleaner.py                 # HealthDataPreprocessor (scaling, feature engineering, sequences)
│   ├── models/
│   │   ├── train_lstm_autoencoder.py       # LSTM autoencoder trainer (TensorFlow, 60-step sequences)
│   │   ├── train_lstm_tflite.py            # Conv1D autoencoder → TFLite export (anomaly)
│   │   ├── train_activity_tflite.py        # Dense NN → TFLite export (activity classification)
│   │   ├── lambda_inference_sklearn.py     # sklearn inference wrapper for Lambda (GB/RF/IF auto-detect)
│   │   └── lambda_inference.py             # LSTM inference wrapper for Lambda (TensorFlow)
│   └── tests/
│       ├── comprehensive_ml_test.py        # Full evaluation: 7 test suites across all model types
│       ├── test_sklearn_models.py          # sklearn model smoke tests
│       ├── test_lambda_export.py           # Lambda export package validation
│       ├── test_integration.py             # End-to-end integration tests
│       ├── tflite_smoketest.py             # TFLite inference validation
│       └── run_all_tests.py                # Test orchestrator
├── data/
│   ├── raw/                                # (empty, placeholder)
│   ├── processed/
│   │   └── health_metrics.csv              # 25,000 rows (20K normal + 5K anomalous, shuffled)
│   └── synthetic/
│       ├── normal_data.csv                 # 20,000 normal samples
│       ├── anomalous_data.csv              # 5,000 samples with injected anomalies
│       ├── exercise_scenario.csv           # 500 samples — elevated HR during exercise (normal)
│       ├── sleep_scenario.csv              # 500 samples — low HR during sleep (normal)
│       ├── tachycardia_scenario.csv        # 500 samples — HR 150-180 at rest (anomaly)
│       └── bradycardia_scenario.csv        # 500 samples — HR 30-45 at rest (anomaly)
├── models/
│   ├── saved_models/                       # Trained model artifacts (.pkl)
│   │   ├── best_anomaly_gradientboosting.pkl   # Best anomaly model (F1=0.995)
│   │   ├── best_anomaly_randomforest.pkl       # Second-best anomaly model
│   │   ├── best_anomaly_scaler.pkl             # StandardScaler for anomaly models
│   │   ├── best_activity_xgboost.pkl           # Best activity model (Acc=85.8%)
│   │   ├── best_activity_extratrees.pkl        # Backup activity model
│   │   ├── best_activity_scaler.pkl            # StandardScaler for activity models
│   │   ├── isolation_forest.pkl                # Unsupervised fallback
│   │   └── scaler.pkl                          # Scaler for Isolation Forest
│   ├── lambda_export/                      # Lambda deployment package
│   │   ├── model.pkl                       # Bundled model + scaler (GradientBoosting)
│   │   └── metadata.json                   # Model type, features, class name
│   ├── tflite/                             # TFLite edge models
│   │   ├── activity_classifier.tflite      # 5 KB — 6-class activity classifier
│   │   ├── activity_classifier.h5          # Keras source model
│   │   ├── activity_classifier_labels.json # Label mapping
│   │   ├── anomaly_lstm.tflite             # 16 KB — Conv1D anomaly autoencoder
│   │   ├── anomaly_lstm.h5                 # Keras source model
│   │   └── anomaly_lstm_signature.json     # Input/output shape metadata
│   └── checkpoints/                        # Training checkpoints
├── train_pipeline_sklearn.sh               # End-to-end: data gen → sklearn training → Lambda export
├── train_pipeline.sh                       # End-to-end: data gen → LSTM training → Lambda export
├── build_edge_models.sh                    # Trains & exports TFLite models, copies to WearOS assets
├── export_for_lambda.sh                    # Converts LSTM .h5 → SavedModel & TFLite for Lambda
├── setup_scripts.sh                        # chmod +x on pipeline scripts
├── requirements.txt                        # Full dependency list (TensorFlow, AWS, etc.)
├── requirements_py312.txt                  # Minimal deps for Python 3.12
├── test_results.json                       # Basic test output
├── test_results_comprehensive.json         # Full evaluation results (March 2026)
└── ML_TRAINING_DEPLOYMENT.md               # Detailed training & deployment guide
```

---

## Setup

### 1. Create Virtual Environment

```bash
cd MLPipeline
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

**For sklearn models (recommended):**
```bash
pip install numpy pandas scikit-learn xgboost joblib matplotlib tqdm
```

**For TFLite/LSTM models (requires Python 3.11 + TensorFlow):**
```bash
pip install -r requirements_py312.txt
# or on macOS ARM:
pip install tensorflow-macos==2.15.0 tensorflow-metal==1.1.0
```

### 3. Generate Synthetic Data

```bash
python src/data/generate_synthetic_data.py
```

This creates 25,000 training samples in `data/processed/health_metrics.csv` plus 4 test scenario files in `data/synthetic/`.

---

## Training Pipelines

### sklearn Pipeline (Gradient Boosting + Isolation Forest)

The primary pipeline. Trains supervised and unsupervised models, exports the best to `models/lambda_export/`:

```bash
bash train_pipeline_sklearn.sh
```

Steps:
1. Creates venv, installs `numpy`, `pandas`, `scikit-learn`
2. Runs `src/data/generate_synthetic_data.py` to generate training data
3. Trains Isolation Forest (unsupervised fallback) and Gradient Boosting (supervised, best F1=0.995)
4. Exports best model to `models/lambda_export/model.pkl` with metadata

### LSTM Pipeline (TensorFlow)

Trains an LSTM autoencoder for sequence-based anomaly detection:

```bash
bash train_pipeline.sh
```

Steps:
1. Creates venv, installs TensorFlow (auto-detects Python version)
2. Generates synthetic data
3. Trains LSTM autoencoder (100 epochs, sequence_length=60, encoding_dim=32)
4. Runs `export_for_lambda.sh` to convert the model to SavedModel + TFLite

### TFLite Edge Models

Builds lightweight models for on-device inference on Wear OS:

```bash
bash build_edge_models.sh
```

Steps:
1. Creates a Python 3.11 venv with TensorFlow
2. Trains activity classifier (Dense NN) and anomaly autoencoder (Conv1D)
3. Exports to TFLite with quantization
4. Copies `.tflite` files to `WearOSApp/app/src/main/assets/models/`

---

## Testing

### Comprehensive Evaluation

```bash
python src/tests/comprehensive_ml_test.py --output test_results_comprehensive.json
```

Runs 7 test suites:
1. Existing Isolation Forest evaluation (pre-retrain baseline)
2. Retrained Isolation Forest with proper scaler
3. Unsupervised model comparison (Isolation Forest vs One-Class SVM vs LOF)
4. Supervised model comparison (Random Forest vs Gradient Boosting vs Extra Trees vs XGBoost)
5. Activity classifier comparison (sklearn models on synthetic activity data)
6. TFLite activity classifier evaluation (requires TensorFlow)
7. TFLite Conv1D autoencoder evaluation (requires TensorFlow)

### Individual Test Suites

```bash
python src/tests/test_sklearn_models.py          # sklearn smoke tests
python src/tests/test_lambda_export.py            # Lambda package validation
python src/tests/test_integration.py              # Integration tests
python src/tests/tflite_smoketest.py --benchmark  # TFLite benchmarks (needs TF)
python src/tests/run_all_tests.py                 # Run everything
```

---

## Deployment

### Deploy to AWS Lambda

The `train_pipeline_sklearn.sh` script automatically exports the best model. To deploy manually:

```bash
# models/lambda_export/ already contains model.pkl (GradientBoosting) + metadata.json
# Upload to S3:
aws s3 cp models/lambda_export/ s3://your-bucket/models/ --recursive

# The Lambda function (CloudBackend/aws-lambda/lambda_inference_sklearn.py)
# loads model.pkl from /opt/ml/model/ and serves predictions.
```

### Deploy TFLite to Wear OS

```bash
bash build_edge_models.sh
# Copies activity_classifier.tflite and anomaly_lstm.tflite
# to WearOSApp/app/src/main/assets/models/
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
