"""
Lambda inference for anomaly detection
Supports both supervised models (GradientBoosting, RandomForest) and
unsupervised models (Isolation Forest) — auto-detects at load time.

Updated Mar 2026: GradientBoosting is the primary model (F1=0.995).
"""

import json
import joblib
import numpy as np
from typing import Dict, List, Tuple

class AnomalyDetector:
    """Anomaly detector supporting supervised and unsupervised sklearn models."""

    def __init__(self, model_pkl_path: str):
        """Load model and scaler from joblib pickle."""
        data = joblib.load(model_pkl_path)
        self.model = data['model']
        self.scaler = data['scaler']

        # Auto-detect model type
        model_class = type(self.model).__name__
        self.is_supervised = hasattr(self.model, 'predict_proba')

        if not self.is_supervised:
            # Isolation Forest uses offset_ for thresholding
            self.threshold = -self.model.offset_ if hasattr(self.model, 'offset_') else 0.5

    def predict(self, metrics: List[Dict]) -> Tuple[bool, float]:
        """
        Predict if metrics are anomalous.

        Args:
            metrics: List of metric dicts with heartRate, steps, calories, distance

        Returns:
            (is_anomaly, anomaly_score) where score is 0-1 (higher = more anomalous)
        """
        # Extract features
        X = []
        for m in metrics:
            X.append([
                m.get('heartRate', m.get('heart_rate', 70)),
                m.get('steps', 0),
                m.get('calories', 0),
                m.get('distance', 0)
            ])

        X = np.array(X, dtype=np.float32)

        # Normalize
        X_scaled = self.scaler.transform(X)

        if self.is_supervised:
            # Supervised model (GradientBoosting, RandomForest, etc.)
            predictions = self.model.predict(X_scaled)
            probas = self.model.predict_proba(X_scaled)[:, 1]  # P(anomaly)

            avg_proba = float(np.mean(probas))
            is_anomaly = np.mean(predictions) > 0.5

            return bool(is_anomaly), avg_proba
        else:
            # Unsupervised model (Isolation Forest)
            scores = self.model.score_samples(X_scaled)
            predictions = self.model.predict(X_scaled)

            # Negate so higher = more anomalous, normalize to 0-1
            avg_score = -np.mean(scores)
            avg_score = np.clip(avg_score / self.threshold, 0, 1)

            is_anomaly = np.mean(predictions == -1) > 0.5

            return bool(is_anomaly), float(avg_score)


# Load model once (cold start)
detector = None

def lambda_handler(event, context):
    """AWS Lambda handler for anomaly detection."""
    global detector

    try:
        if detector is None:
            detector = AnomalyDetector('/opt/ml/model/model.pkl')

        metrics = event.get('metrics', [])
        is_anomaly, score = detector.predict(metrics)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'anomalyDetected': is_anomaly,
                'anomalyScore': score,
                'modelType': type(detector.model).__name__,
                'message': 'Anomaly detection completed'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

