# ML Model Training & Deployment Guide

This guide covers training, evaluating, and deploying ML models for real-time health anomaly detection and activity classification.

## 🏆 Best Models (Tested Feb 2026)

| Task | Best Model | Performance | Model File |
|------|-----------|:-----------:|------------|
| **Anomaly Detection** | Random Forest | F1 = 1.0000 | `best_anomaly_randomforest.pkl` |
| **Activity Classification** | Extra Trees | Acc = 86.20% | `best_activity_extratrees.pkl` |
| Anomaly Detection (unsupervised) | Isolation Forest | F1 = 0.8874 | `isolation_forest.pkl` |
| Edge Anomaly Detection | Conv1D Autoencoder | Partial | `anomaly_lstm.tflite` |
| Edge Activity Classification | Dense NN | Acc = 34.27% | `activity_classifier.tflite` |

### Anomaly Detection Model Rankings

| Rank | Model | F1 | AUC-ROC | Precision | Recall | Type |
|:----:|-------|:--:|:-------:|:---------:|:------:|------|
| 👑 | **Random Forest** | **1.0000** | 1.0000 | 1.0000 | 1.0000 | Supervised |
| #2 | Gradient Boosting | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Supervised |
| #3 | Extra Trees | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Supervised |
| #4 | XGBoost | 0.9883 | 1.0000 | 0.9900 | 0.9867 | Supervised |
| #5 | Isolation Forest | 0.8874 | 0.9955 | 0.9367 | 0.8430 | Unsupervised |
| #6 | One-Class SVM | 0.7221 | 0.8528 | 0.7622 | 0.6860 | Unsupervised |
| #7 | Local Outlier Factor | 0.2053 | 0.4732 | 0.2167 | 0.1950 | Unsupervised |

### Activity Classification Model Rankings

| Rank | Model | Accuracy | Best Per-Class F1 | Worst Per-Class F1 |
|:----:|-------|:--------:|:------------------:|:-------------------:|
| 👑 | **Extra Trees** | **86.20%** | sleep: 0.9247 | exercise: 0.7935 |
| #2 | XGBoost | 85.58% | sleep: 0.9245 | exercise: 0.7837 |
| #3 | Random Forest | 85.42% | sleep: 0.9203 | exercise: 0.7856 |
| #4 | Gradient Boosting | 85.16% | sleep: 0.9266 | exercise: 0.7762 |
| #5 | TFLite Dense NN | 34.27% | sleep: 0.6068 | run: 0.0000 |

## 1) Setup

### Create virtual environment:
```bash
cd MLPipeline
python3 -m venv venv
source venv/bin/activate
pip install numpy pandas scikit-learn xgboost joblib matplotlib tqdm
```

### Generate synthetic data (optional):
```bash
python src/data/generate_synthetic_data.py
# Creates data/processed/health_metrics.csv (25,000 samples)
```

## 2) Train & Evaluate All Models

### Recommended: Run comprehensive test suite
```bash
python src/tests/comprehensive_ml_test.py --output test_results_comprehensive.json
```

This automatically:
1. Evaluates the existing model (shows the before state)
2. Retrains Isolation Forest with proper scaler
3. Compares 7 anomaly detection models (supervised + unsupervised)
4. Compares 4 activity classifiers against TFLite
5. Runs edge case tests (12 physiological scenarios)
6. Performs 5-fold cross-validation
7. Saves the best models to `models/saved_models/`

### Legacy: Train Isolation Forest only
```bash
bash train_pipeline_sklearn.sh
```

### Legacy: Train LSTM Autoencoder
```bash
python src/models/train_lstm_autoencoder.py \
  --data data/processed/health_metrics.csv \
  --epochs 100 \
  --batch-size 32 \
  --sequence-length 60 \
  --encoding-dim 32 \
  --output models/saved_models/lstm_autoencoder.h5
```

## 3) Model Architectures

### Random Forest (Best Anomaly Model)
- **Type**: Supervised ensemble classifier
- **Estimators**: 200 trees, max_depth=10
- **Preprocessing**: StandardScaler normalization
- **Features**: heartRate, steps, calories, distance
- **Class balancing**: `class_weight='balanced'`
- **CV F1**: 1.0000 ± 0.0000

### Extra Trees (Best Activity Classifier)
- **Type**: Supervised ensemble classifier
- **Estimators**: 300 trees, max_depth=15
- **Classes**: sleep, rest, walk, run, exercise, other
- **Preprocessing**: StandardScaler normalization
- **Class balancing**: `class_weight='balanced'`

### LSTM Autoencoder (Deep Learning)
- **Encoder**: Input(60×7) → LSTM(128) → LSTM(64) → LSTM(32)
- **Decoder**: RepeatVector(60) → LSTM(32) → LSTM(64) → LSTM(128) → Dense(7)
- **Loss**: MSE (reconstruction error)
- **Anomaly threshold**: 95th percentile of normal data error

## 4) Export for Lambda

### Convert model for deployment:
```bash
chmod +x export_for_lambda.sh
./export_for_lambda.sh
```

This creates `models/lambda_export/` with:
- **lstm_model_savedmodel/**: TensorFlow SavedModel (portable, ~6–8 MB)
- **lstm_model.tflite**: TensorFlow Lite (ultra-lightweight, ~2–3 MB)
- **threshold.npy**: Anomaly threshold (binary file)
- **lambda_function.py**: Lambda handler
- **requirements.txt**: Dependencies

### Model formats explained:

| Format | Size | Speed | Compatibility | Use case |
|--------|------|-------|---------------|----------|
| SavedModel | 6–8 MB | Fast | All TF versions | Production Lambda |
| TFLite | 2–3 MB | Very fast | Quantized inference | Mobile/Edge |
| .h5 | Similar | Fast | Legacy TF | Training/local |

## 5) Deploy to AWS Lambda

### Option A: Upload to S3 and reference

```bash
# 1. Create S3 bucket
aws s3 mb s3://your-health-models

# 2. Upload model
aws s3 cp models/lambda_export/ s3://your-health-models/lstm/ --recursive

# 3. Create Lambda layer with TensorFlow
# (See CloudBackend/README.md for Lambda layer setup)

# 4. Create Lambda function
aws lambda create-function \
  --function-name health-anomaly-detector \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_export.zip \
  --environment Variables={MODEL_PATH=s3://your-health-models/lstm/lstm_model_savedmodel}
```

### Option B: Embed in Lambda (if model is <50 MB)

```bash
# Package everything
cd models/lambda_export
zip -r lambda_deployment.zip .
cd ../..

# Upload
aws lambda update-function-code \
  --function-name health-anomaly-detector \
  --zip-file fileb://models/lambda_export/lambda_deployment.zip
```

## 6) Invoke the Model

### Request format (from Wear app):
```json
{
  "metrics": [
    {
      "heartRate": 75.0,
      "steps": 120,
      "calories": 45.5,
      "distance": 96.0,
      "hour_sin": 0.5,
      "hour_cos": 0.866,
      "is_weekend": 0
    },
    ...
  ]
}
```

### Response format:
```json
{
  "statusCode": 200,
  "body": {
    "anomalyDetected": false,
    "anomalyScore": 0.23,
    "message": "Anomaly detection completed"
  }
}
```

### Score interpretation:
- **0.0–0.3**: Normal (score < threshold)
- **0.3–0.7**: Borderline (monitor)
- **0.7–1.0**: Anomaly (high confidence)

## 7) Performance Tuning

### Training:
- **Batch size**: Larger (128, 256) for stability; smaller (16, 32) for memory
- **Epochs**: 100–200; early stopping prevents overfitting
- **Sequence length**: 60 samples = 5 minutes at 5-second intervals
- **Encoding dim**: 32 is a good balance; smaller = faster inference, less capacity

### Inference (Lambda):
- **Cold start**: ~2–3s (model loading from disk/S3)
- **Inference time**: ~100–200ms per batch
- **Memory**: ~1–2 GB for SavedModel, ~500 MB for TFLite
- **Throughput**: Process 1–10 metrics per invocation

### Optimization for Lambda:
1. Use **TFLite** for faster startup and lower memory
2. Cache model in Lambda layer (avoid S3 download each invocation)
3. Batch process multiple metrics in one Lambda call
4. Use **Provisioned Concurrency** if invocation rate > 100/min

## 8) Evaluate & Monitor

### After training, check:
```bash
# View training history
less models/training_history.png

# Test on known anomalies
python src/evaluation/evaluate_model.py \
  --model models/saved_models/lstm_autoencoder.h5 \
  --test-data data/synthetic/anomalous_data.csv
```

### In production:
- Monitor reconstruction error distribution
- Track false positive rate
- Adjust threshold (95th percentile) based on user feedback
- Retrain monthly with new data patterns

## 9) Troubleshooting

### Model not converging?
- Check data normalization
- Increase epochs or reduce learning rate dropout
- Verify sequence length matches training data

### Lambda timeout?
- Model is too slow; try TFLite
- Batch size is too large; process fewer metrics per invocation

### High false positive rate?
- Increase threshold (e.g., 98th percentile instead of 95th)
- Retrain with more normal data examples
- Add context (time of day, activity) to reduce false alarms

## 10) Integration with Wear App

The Wear app sends unsynced metrics to Lambda via DataSyncWorker:

1. **HealthRepository.syncMetricsToCloud()** flags suspicious metrics locally
2. **DataSyncWorker** batches and sends to Lambda `/health-data/sync`
3. **Lambda** runs LSTM inference on flagged metrics
4. **Response** includes `anomalyScore` (0–1) for each metric
5. **MainActivity** displays alerts based on cloud score (≥ 0.7 = alert)

---

**References:**
- Training script: `src/models/train_lstm_autoencoder.py`
- Lambda inference: `src/models/lambda_inference.py`
- Preprocessing: `src/preprocessing/data_cleaner.py`
- Data generation: `src/data/generate_synthetic_data.py`
- Export script: `export_for_lambda.sh`
