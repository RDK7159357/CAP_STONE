# ML Model Training & Deployment Guide

This guide walks through training the LSTM autoencoder and deploying it to AWS Lambda for real-time anomaly detection.

## 1) Setup

### Create virtual environment:
```bash
cd MLPipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Generate synthetic data (optional):
```bash
python src/data/generate_synthetic_data.py
# Creates data/processed/health_metrics.csv (25,000 samples)
```

## 2) Train the LSTM Autoencoder

### Basic training:
```bash
python src/models/train_lstm_autoencoder.py \
  --data data/processed/health_metrics.csv \
  --epochs 100 \
  --batch-size 32 \
  --sequence-length 60 \
  --encoding-dim 32 \
  --output models/saved_models/lstm_autoencoder.h5
```

### What this does:
1. Loads 25,000 health metrics samples
2. Preprocesses (normalization, feature engineering)
3. Creates 60-sample sequences (5-minute windows at 5-second intervals)
4. Splits into train/validation (80/20)
5. Trains LSTM autoencoder with 3 layers (128→64→32→64→128)
6. Early stopping and learning rate reduction
7. Calculates 95th percentile threshold for anomaly detection
8. Saves model + threshold + training plots

### Expected output:
```
Training samples: ~10,000 sequences
Validation samples: ~2,500 sequences
Threshold (95th percentile): ~0.0058
Training time: ~30–60 minutes on GPU
Model size: ~4–8 MB
```

## 3) Model Architecture

### Encoder:
```
Input (60 timesteps × 7 features)
  ↓ LSTM(128) + Dropout(0.2)
  ↓ LSTM(64) + Dropout(0.2)
  ↓ LSTM(32) [bottleneck]
```

### Decoder:
```
RepeatVector (60 timesteps)
  ↓ LSTM(32) + Dropout(0.2)
  ↓ LSTM(64) + Dropout(0.2)
  ↓ LSTM(128) + Dropout(0.2)
  ↓ TimeDistributed(Dense(7))
Output (60 timesteps × 7 features)
```

### Features (7 total):
1. `heartRate`: BPM (normalized)
2. `steps`: Step count (normalized)
3. `calories`: Energy expenditure (normalized)
4. `distance`: Distance traveled (normalized)
5. `hour_sin`, `hour_cos`: Cyclical hour encoding
6. `is_weekend`: Binary weekend flag

### Loss function:
- **MSE (Mean Squared Error)** between input and reconstruction
- Autoencoder learns to reconstruct normal data
- Anomalies have high reconstruction error

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
