#!/bin/bash
# Local test runner for Isolation Forest Lambda handler

set -euo pipefail

ROOT="/Users/ramadugudhanush/Documents/CAP_STONE"
HANDLER_SRC="$ROOT/CloudBackend/aws-lambda/lambda_inference_sklearn.py"
MODEL_SRC="$ROOT/MLPipeline/models/lambda_export/model.pkl"
SCALER_SRC="$ROOT/MLPipeline/models/saved_models/scaler.pkl"

echo "🧪 Testing Isolation Forest Lambda Handler"
echo "=========================================="

# Ensure artifacts
if [ ! -f "$MODEL_SRC" ]; then
  echo "❌ Missing model at $MODEL_SRC"; exit 1;
fi

TEST_DIR="/tmp/lambda-test"
rm -rf "$TEST_DIR" && mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Place artifacts where handler expects
cp "$HANDLER_SRC" .
cp "$MODEL_SRC" /tmp/model.pkl
cp "$SCALER_SRC" /tmp/scaler.pkl

# Install deps for local run in a temp venv
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -q --upgrade pip
python3 -m pip install -q numpy scikit-learn joblib boto3
echo "✓ Dependencies installed"
echo ""

run_test() {
  local title="$1"
  local payload="$2"
  echo "$title"
  PAYLOAD="$payload" python3 - <<'PY'
import json, os, sys
sys.path.insert(0, '/tmp/lambda-test')

# Force local model load
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['MODEL_BUCKET'] = ''

from lambda_inference_sklearn import lambda_handler

payload = os.environ['PAYLOAD']
event = {'httpMethod': 'POST', 'body': payload}

resp = lambda_handler(event, None)
body = json.loads(resp['body'])
print(f"  ✓ Status: {resp['statusCode']}")
for i, result in enumerate(body['results'], 1):
    print(f"    [{i}] id={result['metric_id']} anomaly={result['is_anomaly']} score={result['cloud_score']:.4f}")
print(f"  ✓ Model Threshold: {body['model_threshold']:.6f}")
PY
  echo ""
}

run_test "Test 1: Normal heart rate (72 BPM)" '{"metrics": [{"metric_id": "normal-1", "heart_rate": 72, "steps": 150, "calories": 25, "distance": 0.15}]}'
run_test "Test 2: High heart rate (160 BPM - likely anomalous)" '{"metrics": [{"metric_id": "high-hr-1", "heart_rate": 160, "steps": 200, "calories": 50, "distance": 0.3}]}'
run_test "Test 3: Low heart rate (40 BPM - likely anomalous)" '{"metrics": [{"metric_id": "low-hr-1", "heart_rate": 40, "steps": 0, "calories": 0, "distance": 0}]}'
run_test "Test 4: Batch processing (3 metrics)" '{"metrics": [{"metric_id": "batch-1", "heart_rate": 75, "steps": 100, "calories": 20, "distance": 0.1}, {"metric_id": "batch-2", "heart_rate": 150, "steps": 250, "calories": 60, "distance": 0.5}, {"metric_id": "batch-3", "heart_rate": 45, "steps": 10, "calories": 5, "distance": 0.05}]}'

echo "=========================================="
echo "✅ Local Handler Tests Complete"
echo ""
echo "Next steps: deploy to AWS Lambda (see LAMBDA_DEPLOYMENT_GUIDE.md) and test via API Gateway"
