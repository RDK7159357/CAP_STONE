#!/bin/bash
# Quick-start ML pipeline with Scikit-Learn (no TensorFlow needed)

set -e

echo "🚀 Anomaly Detection Model Training Pipeline"
echo "=============================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install/upgrade requirements
echo "Installing dependencies (numpy, pandas, scikit-learn)..."
pip install -q --upgrade pip setuptools wheel
pip install -q numpy pandas scikit-learn matplotlib tqdm joblib

echo "✓ Environment ready"
echo ""

# Step 1: Generate synthetic data
echo "📊 Step 1: Generating synthetic health data..."
python src/data/generate_synthetic_data.py
echo "✓ Generated data/processed/health_metrics.csv"
echo ""

# Step 2: Train the model (Isolation Forest - much faster than LSTM)
echo "🧠 Step 2: Training Isolation Forest anomaly detector..."
echo "   (This takes < 1 minute)"
echo ""

python << 'EOF'
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os

# Create directories
os.makedirs('models/saved_models', exist_ok=True)

# Load data
print("   Loading data...")
df = pd.read_csv('data/processed/health_metrics.csv')

# Select features
features = ['heartRate', 'steps', 'calories', 'distance']
X = df[features].fillna(0)

# Normalize
print("   Normalizing features...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train Isolation Forest (unsupervised anomaly detection)
print("   Training Isolation Forest...")
model = IsolationForest(
    contamination=0.1,  # Expect ~10% anomalies
    random_state=42,
    n_estimators=100
)
predictions = model.fit_predict(X_scaled)
anomaly_scores = model.score_samples(X_scaled)

# Save model and scaler
joblib.dump(model, 'models/saved_models/isolation_forest.pkl')
joblib.dump(scaler, 'models/saved_models/scaler.pkl')

# Statistics
normal_count = np.sum(predictions == 1)
anomaly_count = np.sum(predictions == -1)

print(f"\n   ✓ Model trained!")
print(f"   Normal samples: {normal_count}")
print(f"   Anomalies detected: {anomaly_count}")
print(f"   Threshold (offset_): {model.offset_:.6f}")

EOF

echo ""
echo "✓ Training complete"
echo ""

# Step 3: Create Lambda-ready deployment package
echo "📦 Step 3: Creating Lambda deployment package..."

mkdir -p models/lambda_export

python << 'EOF'
import joblib
import json

# Load models
model = joblib.load('models/saved_models/isolation_forest.pkl')
scaler = joblib.load('models/saved_models/scaler.pkl')

# Save as joblib (lightweight, portable)
joblib.dump({'model': model, 'scaler': scaler}, 'models/lambda_export/model.pkl')

# Save metadata
metadata = {
    'type': 'IsolationForest',
    'features': ['heartRate', 'steps', 'calories', 'distance'],
    'threshold': float(model.offset_),
    'contamination': 0.1
}

with open('models/lambda_export/metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print("Models saved to models/lambda_export/")
EOF

echo "✓ Exported to models/lambda_export/"
echo ""

# Summary
echo "========================================="
echo "✅ Pipeline Complete!"
echo "========================================="
echo ""
echo "Artifacts created:"
echo "  📄 models/saved_models/isolation_forest.pkl"
echo "  📊 models/saved_models/scaler.pkl"
echo "  📦 models/lambda_export/model.pkl"
echo "  📋 models/lambda_export/metadata.json"
echo ""
echo "Model Info:"
echo "  Type: Isolation Forest (fast, unsupervised)"
echo "  Features: heartRate, steps, calories, distance"
echo "  Training time: < 1 minute"
echo "  Inference time: < 5ms per metric"
echo ""
echo "Next steps:"
echo "  1. Deploy models/lambda_export/ to S3"
echo "  2. Create Lambda function with this handler:"
echo "     - Load model.pkl"
echo "     - Call model.predict() on incoming metrics"
echo "     - Return anomaly_score"
echo ""
echo "Note: This uses scikit-learn Isolation Forest instead of TensorFlow LSTM"
echo "      for compatibility with Python 3.14 and faster training."
