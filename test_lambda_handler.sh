#!/bin/bash
# Local test runner for GradientBoosting Lambda handler
# Tests anomaly detection with explainability (anomaly_reasons + feature_contributions)

set -euo pipefail

ROOT="/Users/ramadugudhanush/Documents/CAP_STONE"
HANDLER_SRC="$ROOT/CloudBackend/aws-lambda/lambda_inference_sklearn.py"

# Try GradientBoosting model first, fall back to legacy
GB_MODEL="$ROOT/MLPipeline/models/saved_models/best_anomaly_gradientboosting.pkl"
LEGACY_MODEL="$ROOT/MLPipeline/models/lambda_export/model.pkl"
GB_SCALER="$ROOT/MLPipeline/models/saved_models/best_anomaly_scaler.pkl"
LEGACY_SCALER="$ROOT/MLPipeline/models/saved_models/scaler.pkl"

if [[ -f "$GB_MODEL" ]]; then
    MODEL_SRC="$GB_MODEL"
    SCALER_SRC="$GB_SCALER"
    MODEL_NAME="GradientBoosting"
elif [[ -f "$LEGACY_MODEL" ]]; then
    MODEL_SRC="$LEGACY_MODEL"
    SCALER_SRC="$LEGACY_SCALER"
    MODEL_NAME="Legacy (IsolationForest)"
else
    echo "❌ Missing model. Run: cd MLPipeline && python src/tests/comprehensive_ml_test.py"
    exit 1
fi

echo "🧪 Testing $MODEL_NAME Lambda Handler (with Explainability)"
echo "=========================================="

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
print(f"  ✓ Model: {body.get('model_type', 'unknown')} (supervised={body.get('model_supervised', '?')})")
for i, result in enumerate(body['results'], 1):
    anomaly_str = '⚠️  ANOMALY' if result['is_anomaly'] else '✅ Normal'
    print(f"    [{i}] {anomaly_str} | id={result['metric_id']} score={result['cloud_score']:.4f}")
    reasons = result.get('anomaly_reasons', [])
    if reasons:
        for r in reasons:
            print(f"        → {r}")
    contributions = result.get('feature_contributions', {})
    if contributions:
        sorted_c = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        parts = [f"{k}={v:.1%}" for k, v in sorted_c]
        print(f"        Feature contributions: {', '.join(parts)}")
PY
  echo ""
}

run_test "Test 1: Normal heart rate (72 BPM)" '{"metrics": [{"metric_id": "normal-1", "heart_rate": 72, "steps": 150, "calories": 25, "distance": 0.15}]}'
run_test "Test 2: Tachycardia (180 BPM at rest)" '{"metrics": [{"metric_id": "tachy-1", "heart_rate": 180, "steps": 10, "calories": 5, "distance": 0.01}]}'
run_test "Test 3: Bradycardia (35 BPM)" '{"metrics": [{"metric_id": "brady-1", "heart_rate": 35, "steps": 0, "calories": 0, "distance": 0}]}'
run_test "Test 4: Exercise (high HR + high steps = not anomalous)" '{"metrics": [{"metric_id": "exercise-1", "heart_rate": 155, "steps": 800, "calories": 120, "distance": 2.5}]}'
run_test "Test 5: Batch (normal + anomaly + borderline)" '{"metrics": [{"metric_id": "batch-1", "heart_rate": 75, "steps": 100, "calories": 20, "distance": 0.1}, {"metric_id": "batch-2", "heart_rate": 190, "steps": 5, "calories": 3, "distance": 0.01}, {"metric_id": "batch-3", "heart_rate": 105, "steps": 300, "calories": 60, "distance": 0.5}]}'

echo "=========================================="
echo "✅ Local Handler Tests Complete (with Anomaly Explainability)"
echo ""
echo "Next steps: deploy to AWS Lambda and test via API Gateway"
echo "  cd CloudBackend/aws-lambda && ./deploy.sh"
