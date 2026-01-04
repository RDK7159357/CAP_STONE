#!/bin/bash
# Quick-start ML pipeline: generate data → preprocess → train model

set -e

echo "🚀 LSTM Autoencoder Training Pipeline"
echo "======================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Detect Python version and use appropriate requirements
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo "Using Python $PYTHON_VERSION"

# Install/upgrade requirements
echo "Installing dependencies..."
pip install -q --upgrade pip setuptools wheel

# Use Python 3.12 compatible requirements if available
if [[ "$PYTHON_VERSION" == "3.12" ]] && [ -f "requirements_py312.txt" ]; then
    echo "Using Python 3.12 compatible dependencies..."
    pip install -q -r requirements_py312.txt
else
    pip install -q -r requirements.txt
fi

echo "✓ Environment ready"
echo ""

# Step 1: Generate synthetic data
echo "📊 Step 1: Generating synthetic health data..."
python src/data/generate_synthetic_data.py
echo "✓ Generated data/processed/health_metrics.csv"
echo ""

# Step 2: Train the model
echo "🧠 Step 2: Training LSTM Autoencoder..."
echo "   (This may take 5-30 minutes depending on your hardware)"
echo ""

python src/models/train_lstm_autoencoder.py \
  --data data/processed/health_metrics.csv \
  --epochs 100 \
  --batch-size 32 \
  --sequence-length 60 \
  --encoding-dim 32 \
  --output models/saved_models/lstm_autoencoder.h5

echo ""
echo "✓ Training complete"
echo ""

# Step 3: Export for Lambda
echo "📦 Step 3: Exporting for Lambda deployment..."
bash export_for_lambda.sh
echo "✓ Exported to models/lambda_export/"
echo ""

# Summary
echo "========================================="
echo "✅ Pipeline Complete!"
echo "========================================="
echo ""
echo "Artifacts created:"
echo "  📄 models/saved_models/lstm_autoencoder.h5"
echo "  📊 models/training_history.png"
echo "  📦 models/lambda_export/ (ready for deployment)"
echo ""
echo "Next steps:"
echo "  1. Review models/training_history.png"
echo "  2. Upload models/lambda_export/ to S3"
echo "  3. Deploy Lambda function with the model"
echo "  4. Set ApiConfig.BASE_URL in Wear app to your Lambda endpoint"
echo ""
echo "For details, see MLPipeline/ML_TRAINING_DEPLOYMENT.md"
