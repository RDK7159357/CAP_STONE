import json
import boto3
import logging
from datetime import datetime
from decimal import Decimal
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'HealthMetrics')
table = dynamodb.Table(table_name)

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-API-Key',
    'Access-Control-Allow-Methods': 'POST,GET,OPTIONS'
}

def lambda_handler(event, context):
    """
    Main Lambda handler for health data ingestion
    """
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': ''
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate API key (basic authentication)
        api_key = event.get('headers', {}).get('X-API-Key', '')
        if not validate_api_key(api_key):
            return error_response(401, 'Unauthorized: Invalid API key')
        
        # Determine if single or batch ingestion
        if isinstance(body, list):
            result = handle_batch_ingestion(body)
        else:
            result = handle_single_ingestion(body)
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return error_response(500, f'Internal server error: {str(e)}')


def handle_single_ingestion(data):
    """
    Handle single health metric ingestion
    """
    # Validate required fields
    required_fields = ['userId', 'timestamp', 'metrics', 'deviceId']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # Optional edge-ML fields
    is_anomalous_edge = data.get('isAnomalous', False)
    local_score = data.get('localAnomalyScore')
    edge_score = data.get('edgeAnomalyScore')
    activity_state = data.get('activityState')
    model_version = data.get('modelVersion')

    # Prepare item for DynamoDB
    item = {
        'userId': data['userId'],
        'timestamp': int(data['timestamp']),
        'deviceId': data['deviceId'],
        'metrics': convert_floats_to_decimal(data['metrics']),
        'receivedAt': int(datetime.now().timestamp() * 1000),
        'anomalyDetected': bool(is_anomalous_edge) or False
    }

    if local_score is not None:
        item['localAnomalyScore'] = convert_floats_to_decimal(local_score)
    if edge_score is not None:
        item['edgeAnomalyScore'] = convert_floats_to_decimal(edge_score)
    if activity_state is not None:
        item['activityState'] = activity_state
    if model_version is not None:
        item['modelVersion'] = model_version
    
    # Store in DynamoDB
    table.put_item(Item=item)
    logger.info(f"Stored metric for user {data['userId']} at {data['timestamp']}")
    
    # Check for anomalies (placeholder - will be replaced by ML model)
    anomaly_detected = check_for_anomalies(data['metrics'], edge_score)
    
    if anomaly_detected:
        # Update item with anomaly flag
        table.update_item(
            Key={
                'userId': data['userId'],
                'timestamp': int(data['timestamp'])
            },
            UpdateExpression='SET anomalyDetected = :val',
            ExpressionAttributeValues={':val': True}
        )
        
        # Trigger notification (if needed)
        send_anomaly_notification(data['userId'], data['metrics'])
    
    return {
        'success': True,
        'message': 'Data ingested successfully',
        'anomalyDetected': anomaly_detected
    }


def handle_batch_ingestion(data_list):
    """
    Handle batch ingestion of multiple health metrics
    """
    success_count = 0
    error_count = 0
    anomalies_detected = 0
    
    for data in data_list:
        try:
            result = handle_single_ingestion(data)
            success_count += 1
            if result.get('anomalyDetected'):
                anomalies_detected += 1
        except Exception as e:
            logger.error(f"Error ingesting item: {str(e)}")
            error_count += 1
    
    return {
        'success': True,
        'message': f'Batch ingestion completed',
        'successCount': success_count,
        'errorCount': error_count,
        'anomaliesDetected': anomalies_detected
    }


def check_for_anomalies(metrics, edge_score=None):
    """
    Hybrid anomaly detection: prefer edge score if provided; otherwise fall back to thresholds.
    """
    # If edge model provided a score, use it (>=0.5 anomalous)
    if edge_score is not None:
        try:
            score_f = float(edge_score)
            if score_f >= 0.5:
                logger.warning(f"Anomaly detected via edge score: {score_f}")
                return True
        except Exception:
            pass

    # Fallback: Simple threshold-based detection
    heart_rate = metrics.get('heartRate')
    if heart_rate is not None:
        if heart_rate > 150 or heart_rate < 40:
            logger.warning(f"Anomaly detected: Heart rate {heart_rate} BPM")
            return True

    return False


def send_anomaly_notification(user_id, metrics):
    """
    Send notification for detected anomaly
    TODO: Integrate with SNS or Firebase Cloud Messaging
    """
    logger.info(f"Anomaly notification for user {user_id}: {metrics}")
    
    # Placeholder for SNS integration
    # sns = boto3.client('sns')
    # sns.publish(
    #     TopicArn='arn:aws:sns:region:account:health-alerts',
    #     Message=f'Anomaly detected for user {user_id}',
    #     Subject='Health Alert'
    # )


def validate_api_key(api_key):
    """
    Validate API key
    TODO: Implement proper API key validation with Secrets Manager
    """
    # For development, accept any non-empty key
    # In production, validate against stored keys
    return len(api_key) > 0


def convert_floats_to_decimal(obj):
    """
    Convert float values to Decimal for DynamoDB compatibility
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(i) for i in obj]
    return obj


def success_response(data):
    """
    Return success response with CORS headers
    """
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps(data)
    }


def error_response(status_code, message):
    """
    Return error response with CORS headers
    """
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }
