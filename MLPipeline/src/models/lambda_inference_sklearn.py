"""
Lambda inference using Isolation Forest
Lightweight, fast anomaly detection for AWS Lambda
"""

import json
import joblib
import numpy as np
from typing import Dict, List, Tuple

class AnomalyDetector:
    """Isolation Forest anomaly detector for health metrics"""
    
    def __init__(self, model_pkl_path: str):
        """Load model and scaler from joblib"""
        data = joblib.load(model_pkl_path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.threshold = -self.model.offset
        
    def predict(self, metrics: List[Dict]) -> Tuple[bool, float]:
        """
        Predict if metrics are anomalous
        
        Args:
            metrics: List of metric dicts with heartRate, steps, calories, distance
            
        Returns:
            (is_anomaly, anomaly_score)
        """
        # Extract features
        X = []
        for m in metrics:
            X.append([
                m.get('heartRate', 70),
                m.get('steps', 0),
                m.get('calories', 0),
                m.get('distance', 0)
            ])
        
        X = np.array(X)
        
        # Normalize
        X_scaled = self.scaler.transform(X)
        
        # Get anomaly scores
        scores = self.model.score_samples(X_scaled)
        predictions = self.model.predict(X_scaled)
        
        # Average score for batch
        avg_score = -np.mean(scores)  # Negate so higher = more anomalous
        avg_score = np.clip(avg_score / self.threshold, 0, 1)  # Normalize to 0-1
        
        is_anomaly = np.mean(predictions == -1) > 0.5
        
        return bool(is_anomaly), float(avg_score)


# Load model once (cold start)
detector = None

def lambda_handler(event, context):
    """AWS Lambda handler"""
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
                'message': 'Anomaly detection completed'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
