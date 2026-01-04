"""
Lambda inference wrapper for LSTM autoencoder deployed to AWS Lambda
This module converts the trained model to a lightweight format suitable for Lambda
"""

import json
import numpy as np
import tensorflow as tf
from typing import Dict, List, Tuple
import os

class HealthAnomalyDetector:
    """
    Wrapper for LSTM autoencoder inference in Lambda environment
    Optimized for AWS Lambda constraints (memory, execution time)
    """
    
    def __init__(self, model_path: str, threshold: float = 0.006):
        """
        Initialize the detector
        
        Args:
            model_path: Path to saved LSTM model (SavedModel format)
            threshold: Reconstruction error threshold (95th percentile)
        """
        self.model = tf.keras.models.load_model(model_path)
        self.threshold = threshold
        self.sequence_length = 60  # Match training sequence length
        self.n_features = 7  # heartRate, steps, calories, distance, hour_sin, hour_cos, is_weekend
        
    def predict_single(self, metric_dict: Dict) -> Tuple[bool, float]:
        """
        Predict anomaly for a single metric
        
        Args:
            metric_dict: Dict with keys: heartRate, steps, calories, distance, 
                        hour_sin, hour_cos, is_weekend
                        
        Returns:
            (is_anomaly, anomaly_score)
        """
        # Normalize input
        feature_vector = np.array([
            metric_dict.get('heartRate', 70),
            metric_dict.get('steps', 0),
            metric_dict.get('calories', 0),
            metric_dict.get('distance', 0),
            metric_dict.get('hour_sin', 0),
            metric_dict.get('hour_cos', 1),
            metric_dict.get('is_weekend', 0)
        ], dtype=np.float32)
        
        # Reshape to (1, 1, 7) for model
        feature_vector = feature_vector.reshape(1, 1, -1)
        
        # Get reconstruction
        reconstruction = self.model.predict(feature_vector, verbose=0)
        
        # Calculate MSE
        mse = np.mean(np.power(feature_vector - reconstruction, 2))
        
        # Determine anomaly
        is_anomaly = float(mse) > self.threshold
        anomaly_score = min(1.0, float(mse) / self.threshold)  # Normalize to 0-1
        
        return is_anomaly, anomaly_score
    
    def predict_sequence(self, metric_sequence: List[Dict]) -> Tuple[bool, float]:
        """
        Predict anomaly for a sequence of metrics
        
        Args:
            metric_sequence: List of metric dicts, length should be ~60
            
        Returns:
            (is_anomaly, anomaly_score)
        """
        # Pad or truncate to sequence length
        if len(metric_sequence) < self.sequence_length:
            metric_sequence = metric_sequence + [metric_sequence[-1]] * (self.sequence_length - len(metric_sequence))
        else:
            metric_sequence = metric_sequence[-self.sequence_length:]
        
        # Convert to numpy array
        X = []
        for metric in metric_sequence:
            X.append([
                metric.get('heartRate', 70),
                metric.get('steps', 0),
                metric.get('calories', 0),
                metric.get('distance', 0),
                metric.get('hour_sin', 0),
                metric.get('hour_cos', 1),
                metric.get('is_weekend', 0)
            ])
        
        X = np.array(X, dtype=np.float32).reshape(1, self.sequence_length, -1)
        
        # Predict
        reconstruction = self.model.predict(X, verbose=0)
        mse = np.mean(np.power(X - reconstruction, 2))
        
        is_anomaly = float(mse) > self.threshold
        anomaly_score = min(1.0, float(mse) / self.threshold)
        
        return is_anomaly, anomaly_score


# Lambda handler
detector = None

def lambda_handler(event, context):
    """
    AWS Lambda handler for anomaly detection
    
    Expected event format:
    {
        "metrics": [
            {
                "heartRate": 75.0,
                "steps": 100,
                "calories": 50.0,
                "distance": 80.0,
                "hour_sin": 0.5,
                "hour_cos": 0.866,
                "is_weekend": 0
            }
        ]
    }
    """
    global detector
    
    try:
        if detector is None:
            # Load model from /opt/ml/model (mounted volume in Lambda)
            model_path = os.getenv('MODEL_PATH', '/opt/ml/model')
            detector = HealthAnomalyDetector(model_path)
        
        metrics = event.get('metrics', [])
        
        if len(metrics) == 1:
            # Single metric prediction
            is_anomaly, score = detector.predict_single(metrics[0])
        else:
            # Sequence prediction
            is_anomaly, score = detector.predict_sequence(metrics)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'anomalyDetected': is_anomaly,
                'anomalyScore': float(score),
                'message': 'Anomaly detection completed'
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Anomaly detection failed'
            })
        }


if __name__ == '__main__':
    # Test the detector
    print("Testing LSTM Autoencoder Detector...")
    
    detector = HealthAnomalyDetector('models/saved_models/lstm_autoencoder.h5')
    
    # Test single metric
    test_metric = {
        'heartRate': 75.0,
        'steps': 100,
        'calories': 50.0,
        'distance': 80.0,
        'hour_sin': 0.5,
        'hour_cos': 0.866,
        'is_weekend': 0
    }
    
    is_anomaly, score = detector.predict_single(test_metric)
    print(f"Single metric - Anomaly: {is_anomaly}, Score: {score:.4f}")
    
    # Test anomalous metric
    anomalous_metric = test_metric.copy()
    anomalous_metric['heartRate'] = 155.0  # High HR
    is_anomaly, score = detector.predict_single(anomalous_metric)
    print(f"Anomalous metric - Anomaly: {is_anomaly}, Score: {score:.4f}")
