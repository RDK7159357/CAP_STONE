Place your TensorFlow Lite models here:
- activity_classifier.tflite : multi-class activity model (e.g., sleep/rest/walk/run/exercise/other)
- anomaly_lstm.tflite : LSTM autoencoder (or classifier) for anomaly scoring

Current files are placeholders to allow builds; replace them with real models.

Input/output expectations (EdgeMlEngine defaults):
- Input tensor: 1x4 float [heartRate, steps, calories, distance]
- activity_classifier output: 1x6 softmax probabilities (labels: sleep, rest, walk, run, exercise, other)
- anomaly_lstm output: 1x1 score in [0,1], where >= 0.5 is anomalous

Regenerating a simple anomaly LSTM (reference):
python train_lstm_tflite.py --epochs 5 --seq-len 10 --out-dir models/tflite
Then copy models/tflite/anomaly_lstm.tflite here.
