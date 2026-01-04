"""
AWS Lambda handler for Isolation Forest anomaly detection.
Loads trained scikit-learn model and scores incoming health metrics.
"""
import json
import boto3
import logging
import joblib
import numpy as np
import os
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# S3 client for model download
s3_client = boto3.client('s3')

# Global model cache
_detector = None
_model = None
_scaler = None

# Model configuration
MODEL_BUCKET = os.environ.get('MODEL_BUCKET', 'health-ml-models')
MODEL_KEY = os.environ.get('MODEL_KEY', 'isolation_forest/model.pkl')
SCALER_KEY = os.environ.get('SCALER_KEY', 'isolation_forest/scaler.pkl')
LOCAL_MODEL_PATH = '/tmp/model.pkl'
LOCAL_SCALER_PATH = '/tmp/scaler.pkl'

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-API-Key',
    'Access-Control-Allow-Methods': 'POST,OPTIONS'
}


class AnomalyDetector:
    """Encapsulates Isolation Forest model and inference logic."""
    
    def __init__(self, model, scaler):
        self.model = model
        self.scaler = scaler
        # IsolationForest offset_ is the decision threshold; anomalies have score < offset_
        self.threshold = float(self.model.offset_)
        
    def predict(self, metrics_list):
        """
        Score a batch of health metrics for anomalies.
        
        Args:
            metrics_list: List of dicts with keys: heart_rate, steps, calories, distance
        
        Returns:
            List of dicts: [{"metric_id": "...", "is_anomaly": bool, "score": float}, ...]
        """
        results = []
        
        for metric in metrics_list:
            try:
                # Extract features in order: [heart_rate, steps, calories, distance]
                features = np.array([[
                    metric.get('heart_rate', 0),
                    metric.get('steps', 0),
                    metric.get('calories', 0),
                    metric.get('distance', 0)
                ]])
                
                # Normalize using fitted scaler
                features_scaled = self.scaler.transform(features)
                
                # Raw score; anomalies when score < threshold
                score = float(self.model.score_samples(features_scaled)[0])
                
                # Normalize score to 0-1 via sigmoid for reporting only
                normalized_score = float(1.0 / (1.0 + np.exp(-score)))
                
                is_anomaly = score < self.threshold
                
                results.append({
                    'metric_id': metric.get('metric_id', ''),
                    'is_anomaly': bool(is_anomaly),
                    'cloud_score': float(normalized_score)
                })
                
            except Exception as e:
                logger.error(f"Error scoring metric {metric.get('metric_id', 'unknown')}: {str(e)}")
                results.append({
                    'metric_id': metric.get('metric_id', ''),
                    'is_anomaly': False,
                    'cloud_score': 0.5,
                    'error': str(e)
                })
        
        return results


def load_model():
    """Lazy-load model and scaler from S3 on first invocation."""
    global _model, _scaler, _detector
    
    if _detector is not None:
        return _detector
    
    try:
        # Download from S3 if not in /tmp
        if not os.path.exists(LOCAL_MODEL_PATH):
            logger.info(f"Downloading model from s3://{MODEL_BUCKET}/{MODEL_KEY}")
            s3_client.download_file(MODEL_BUCKET, MODEL_KEY, LOCAL_MODEL_PATH)
        
        if not os.path.exists(LOCAL_SCALER_PATH):
            logger.info(f"Downloading scaler from s3://{MODEL_BUCKET}/{SCALER_KEY}")
            s3_client.download_file(MODEL_BUCKET, SCALER_KEY, LOCAL_SCALER_PATH)
        
        # Load pickled artifacts
        loaded_model = joblib.load(LOCAL_MODEL_PATH)
        loaded_scaler = joblib.load(LOCAL_SCALER_PATH)

        # Support both direct model pickle and dict bundle {model, scaler}
        if isinstance(loaded_model, dict):
            _model = loaded_model.get('model', loaded_model.get('detector', None))
            if loaded_scaler is None and 'scaler' in loaded_model:
                _scaler = loaded_model['scaler']
        else:
            _model = loaded_model
            _scaler = loaded_scaler

        if _scaler is None:
            _scaler = loaded_scaler
        
        logger.info("Model and scaler loaded successfully")
        
        # Initialize detector
        _detector = AnomalyDetector(_model, _scaler)
        
        return _detector
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}", exc_info=True)
        raise


def lambda_handler(event, context):
    """
    Main Lambda handler for anomaly detection scoring.
    
    Expected request body:
    {
        "metrics": [
            {
                "metric_id": "...",
                "heart_rate": 72,
                "steps": 150,
                "calories": 25,
                "distance": 0.15
            },
            ...
        ]
    }
    
    Response:
    {
        "statusCode": 200,
        "body": {
            "results": [
                {
                    "metric_id": "...",
                    "is_anomaly": false,
                    "cloud_score": 0.15
                },
                ...
            ],
            "timestamp": "2024-01-15T10:30:45Z",
            "model_threshold": -0.123456
        }
    }
    """
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': ''
            }
        
        # Parse request
        body = json.loads(event.get('body', '{}'))
        metrics = body.get('metrics', [])
        
        if not metrics:
            return error_response(400, 'Missing "metrics" field in request body')
        
        # Load model (cached on warm starts)
        detector = load_model()
        
        # Score metrics
        results = detector.predict(metrics)
        
        # Return response
        response_body = {
            'results': results,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'model_threshold': float(detector.threshold)
        }
        
        logger.info(f"Scored {len(results)} metrics, {sum(1 for r in results if r['is_anomaly'])} anomalies detected")
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Error in anomaly detection: {str(e)}", exc_info=True)
        return error_response(500, f'Anomaly detection failed: {str(e)}')


def error_response(status_code, message):
    """Format error response."""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    }
