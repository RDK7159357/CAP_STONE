#!/bin/bash
set -euo pipefail

# Build edge TFLite models (activity + anomaly LSTM)
# Requires Python 3.11 with TensorFlow installed.

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$ROOT/models/tflite"
PYTHON_BIN=${PYTHON_BIN:-python3.11}
EPOCHS=${EPOCHS:-5}
SEQ_LEN=${SEQ_LEN:-10}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.11 not found. Set PYTHON_BIN to a TF-compatible interpreter." >&2
  exit 1
fi

cd "$ROOT"

# Create fresh venv with specified interpreter
rm -rf venv
"$PYTHON_BIN" -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip >/dev/null

# macOS/arm uses tensorflow-macos; fallback to tensorflow for other platforms
if [[ "$(uname -s)" == "Darwin" ]]; then
  python -m pip install "tensorflow-macos==2.15.0" >/dev/null
  # Optional Metal acceleration; ignore failure
  python -m pip install "tensorflow-metal==1.1.0" >/dev/null || true
else
  python -m pip install "tensorflow==2.15.*" >/dev/null
fi
mkdir -p "$OUT_DIR"

echo "Training activity classifier..."
python src/models/train_activity_tflite.py --epochs "$EPOCHS" --out-dir "$OUT_DIR"

echo "Training anomaly LSTM..."
python src/models/train_lstm_tflite.py --epochs "$EPOCHS" --seq-len "$SEQ_LEN" --out-dir "$OUT_DIR"

echo "Build complete. TFLite files in $OUT_DIR"

echo "Copying to Wear app assets..."
ASSETS_DIR="$ROOT/../WearOSApp/app/src/main/assets/models"
mkdir -p "$ASSETS_DIR"
cp "$OUT_DIR"/activity_classifier.tflite "$ASSETS_DIR"/
cp "$OUT_DIR"/anomaly_lstm.tflite "$ASSETS_DIR"/

echo "Done."
