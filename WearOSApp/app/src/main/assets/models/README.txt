TensorFlow Lite models for on-device inference:

1. activity_classifier.tflite
   - Task: Multi-class activity classification (sleep/rest/walk/run/exercise/other)
   - Architecture: Dense NN (4 → 32 → 32 → 6 softmax)
   - Input: [1, 4] float32 — [heartRate, steps, calories, distance]
   - Output: [1, 6] softmax probabilities
   - Size: ~15KB
   - Current Accuracy: 34.3% (Normalization layer not adapted)
   - NOTE: Cloud model (Extra Trees) achieves 86.2% — see MLPipeline/README.md

2. anomaly_lstm.tflite
   - Task: Anomaly detection via sequence reconstruction error
   - Architecture: Conv1D autoencoder (seq_len=10, feat_dim=4)
   - Input: [1, 10, 4] float32 — sequence of [heartRate, steps, calories, distance]
   - Output: [1, 10, 4] reconstructed sequence
   - Size: ~50KB
   - Anomaly scoring: MSE between input and output
     Normal MSE: ~19.56, Tachycardia MSE: ~91.89, Extreme: ~3973
     WARNING: Bradycardia MSE (6.63) is LOWER than normal — cannot detect bradycardia
   - NOTE: Cloud model (Random Forest, F1=1.00) is significantly more accurate

Regenerating models:
  cd MLPipeline
  source venv/bin/activate
  python src/models/train_activity_tflite.py
  python src/models/train_lstm_tflite.py
  cp models/tflite/*.tflite ../WearOSApp/app/src/main/assets/models/

Best cloud models (for reference):
  Anomaly detection: best_anomaly_randomforest.pkl (F1=1.00)
  Activity classification: best_activity_extratrees.pkl (Accuracy=86.2%)
  Location: MLPipeline/models/saved_models/
