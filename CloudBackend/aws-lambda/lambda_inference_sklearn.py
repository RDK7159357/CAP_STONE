"""
AWS Lambda handler for anomaly detection.
Loads trained scikit-learn model and scores incoming health metrics.

Model: GradientBoostingClassifier (F1=0.995, AUC-ROC=1.00)
  - 100 estimators, max_depth=4, min_samples_leaf=5, max_features='sqrt'
  - Trained on 4 features: heartRate, steps, calories, distance
  - StandardScaler normalization applied before prediction

Previous model: Random Forest (F1=0.983) — replaced Mar 2026
"""
import json
import boto3
import logging
import joblib
import numpy as np
import os
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
MODEL_KEY = os.environ.get('MODEL_KEY', 'gradientboosting/model.pkl')
SCALER_KEY = os.environ.get('SCALER_KEY', 'gradientboosting/scaler.pkl')
LOCAL_MODEL_PATH = '/tmp/model.pkl'
LOCAL_SCALER_PATH = '/tmp/scaler.pkl'

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-API-Key',
    'Access-Control-Allow-Methods': 'POST,OPTIONS'
}


class AnomalyDetector:
    """Encapsulates ML model and inference logic for health anomaly detection.
    
    Best Model: GradientBoostingClassifier
      - F1-Score: 0.9950 (5-fold CV: 0.9950 ± 0.0016)
      - AUC-ROC: 1.0000
      - Precision: 0.9934, Recall: 0.9967
    
    Also supports legacy Isolation Forest models for backward compatibility.
    """

    # Feature names in model order
    FEATURE_NAMES = ['heartRate', 'steps', 'calories', 'distance']
    FEATURE_UNITS = {'heartRate': 'BPM', 'steps': 'steps', 'calories': 'kcal', 'distance': 'km'}

    # Normal ranges for human-readable explanations (based on training data)
    NORMAL_RANGES = {
        'heartRate': (50, 100, 'Resting heart rate'),
        'steps':     (0, 500, 'Steps per interval'),
        'calories':  (0, 150, 'Calories per interval'),
        'distance':  (0, 2.0, 'Distance per interval'),
    }
    
    def __init__(self, model, scaler):
        self.model = model
        self.scaler = scaler
        self.model_type = type(model).__name__
        
        # Determine threshold based on model type
        if hasattr(model, 'offset_'):
            # Legacy Isolation Forest
            self.threshold = float(model.offset_)
            self.is_supervised = False
        else:
            # Supervised models (Random Forest, Gradient Boosting, etc.)
            self.threshold = 0.5  # Default probability threshold
            self.is_supervised = True

        # Extract feature importances if available (GradientBoosting, RandomForest, etc.)
        if hasattr(model, 'feature_importances_'):
            self.feature_importances = model.feature_importances_
        else:
            self.feature_importances = None
        
        logger.info(f"Loaded model: {self.model_type} (supervised={self.is_supervised})")
        
    def predict(self, metrics_list):
        """
        Score a batch of health metrics for anomalies, with human-readable explanations.
        
        Args:
            metrics_list: List of dicts with keys: heart_rate, steps, calories, distance
        
        Returns:
            List of dicts: [{
                "metric_id": "...",
                "is_anomaly": bool,
                "score": float,
                "anomaly_reasons": ["Heart rate 180 BPM is above normal range (50–100 BPM)", ...],
                "feature_contributions": {"heartRate": 0.72, "steps": 0.15, ...}
            }, ...]
        """
        results = []
        
        for metric in metrics_list:
            try:
                raw_values = {
                    'heartRate': metric.get('heart_rate', 0),
                    'steps':     metric.get('steps', 0),
                    'calories':  metric.get('calories', 0),
                    'distance':  metric.get('distance', 0),
                }

                # Extract features in order: [heart_rate, steps, calories, distance]
                features = np.array([[
                    raw_values['heartRate'],
                    raw_values['steps'],
                    raw_values['calories'],
                    raw_values['distance'],
                ]])
                
                # Normalize using fitted scaler
                features_scaled = self.scaler.transform(features)
                
                if self.is_supervised:
                    # Supervised model (Random Forest, Gradient Boosting, etc.)
                    prediction = int(self.model.predict(features_scaled)[0])
                    probabilities = self.model.predict_proba(features_scaled)[0]
                    anomaly_probability = float(probabilities[1])  # P(anomaly)
                    is_anomaly = prediction == 1
                    normalized_score = anomaly_probability
                else:
                    # Unsupervised model (Isolation Forest) — legacy support
                    score = float(self.model.score_samples(features_scaled)[0])
                    normalized_score = float(1.0 / (1.0 + np.exp(-score)))
                    is_anomaly = score < self.threshold

                # Generate explanations
                reasons, contributions = self._explain_anomaly(
                    raw_values, features_scaled, is_anomaly, normalized_score
                )
                
                results.append({
                    'metric_id': metric.get('metric_id', ''),
                    'is_anomaly': bool(is_anomaly),
                    'cloud_score': float(normalized_score),
                    'model_type': self.model_type,
                    'anomaly_reasons': reasons,
                    'feature_contributions': contributions,
                })
                
            except Exception as e:
                logger.error(f"Error scoring metric {metric.get('metric_id', 'unknown')}: {str(e)}")
                results.append({
                    'metric_id': metric.get('metric_id', ''),
                    'is_anomaly': False,
                    'cloud_score': 0.5,
                    'anomaly_reasons': [],
                    'feature_contributions': {},
                    'error': str(e)
                })
        
        return results

    def _explain_anomaly(self, raw_values, features_scaled, is_anomaly, score):
        """
        Generate human-readable explanations for why an anomaly was (or was not) detected.
        
        Uses two complementary strategies:
        1. Range-based: compare raw feature values against known normal ranges.
        2. Importance-weighted: use model feature_importances_ to rank which
           features contributed most to the anomaly score.
        
        Args:
            raw_values: dict of original feature values (unscaled)
            features_scaled: numpy array of scaled features [1, n_features]
            is_anomaly: bool prediction result
            score: float anomaly probability / score
        
        Returns:
            (reasons: list[str], contributions: dict[str, float])
        """
        reasons = []
        contributions = {}

        # --- 1. Range-based explanations (always computed) ---
        for i, name in enumerate(self.FEATURE_NAMES):
            val = raw_values[name]
            lo, hi, label = self.NORMAL_RANGES[name]
            unit = self.FEATURE_UNITS[name]

            if val > hi:
                reasons.append(
                    f"{label}: {val:.0f} {unit} is above normal range ({lo}–{hi} {unit})"
                )
            elif val < lo:
                reasons.append(
                    f"{label}: {val:.0f} {unit} is below normal range ({lo}–{hi} {unit})"
                )

        # --- 2. Feature-importance-weighted contributions ---
        if self.feature_importances is not None:
            # Compute per-feature deviation from scaler mean (in std units)
            if hasattr(self.scaler, 'mean_') and hasattr(self.scaler, 'scale_'):
                deviations = np.abs(features_scaled[0])  # already (x - mean) / std
                weighted = deviations * self.feature_importances
                total = weighted.sum() if weighted.sum() > 0 else 1.0
                for i, name in enumerate(self.FEATURE_NAMES):
                    contributions[name] = round(float(weighted[i] / total), 4)

                # If anomaly detected but no range-based reasons fired,
                # add top-contributing feature as explanation
                if is_anomaly and not reasons:
                    top_idx = int(np.argmax(weighted))
                    top_name = self.FEATURE_NAMES[top_idx]
                    top_val = raw_values[top_name]
                    unit = self.FEATURE_UNITS[top_name]
                    pct = contributions[top_name] * 100
                    reasons.append(
                        f"Unusual {top_name} value ({top_val:.0f} {unit}) "
                        f"contributed {pct:.0f}% to anomaly score"
                    )

        # --- 3. High-level summary ---
        if is_anomaly and not reasons:
            # Fallback: generic reason with the model score
            reasons.append(
                f"Model confidence: {score:.1%} probability of anomaly"
            )

        return reasons, contributions


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
        
        model_type = type(_model).__name__
        logger.info(f"Model loaded successfully: {model_type}")
        
        # Initialize detector
        _detector = AnomalyDetector(_model, _scaler)
        
        return _detector
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}", exc_info=True)
        raise


def lambda_handler(event, context):
    """
    Main Lambda handler for anomaly detection scoring.
    
    Model: GradientBoostingClassifier (F1=0.995, 5-fold CV)
    Features: heart_rate, steps, calories, distance
    Preprocessing: StandardScaler normalization
    
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
                    "cloud_score": 0.02,
                    "model_type": "GradientBoostingClassifier"
                },
                ...
            ],
            "timestamp": "2026-03-06T10:30:45Z",
            "model_type": "GradientBoostingClassifier"
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
        
        # Parse request — support both API Gateway (body as JSON string)
        # and direct Lambda invocation (metrics at top level)
        if 'body' in event:
            # API Gateway event: body is a JSON-encoded string
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            # Direct invocation: the event IS the payload
            body = event
        
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
            'model_type': detector.model_type,
            'model_supervised': detector.is_supervised
        }
        
        anomaly_count = sum(1 for r in results if r['is_anomaly'])
        logger.info(f"Scored {len(results)} metrics with {detector.model_type}, "
                     f"{anomaly_count} anomalies detected")
        
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
