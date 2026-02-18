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
lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')
table_name = os.environ.get('TABLE_NAME', 'HealthMetrics')
table = dynamodb.Table(table_name)
push_table_name = os.environ.get('PUSH_TOKEN_TABLE', 'HealthPushTokens')
push_table = dynamodb.Table(push_table_name)
cloud_inference_function = os.environ.get('CLOUD_INFERENCE_FUNCTION', '').strip()
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN', '').strip()
expected_api_key = os.environ.get('API_KEY', '').strip()

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
        # API Gateway normalizes headers - check case-insensitively
        headers = event.get('headers', {})
        api_key = headers.get('X-API-Key') or headers.get('x-api-key') or ''
        if not validate_api_key(api_key):
            logger.warning(f"API key validation failed. Headers: {list(headers.keys())}")
            return error_response(401, 'Unauthorized: Invalid API key')
        
        # Route notification token registration
        path = event.get('path', '')
        if event.get('httpMethod') == 'POST' and path.endswith('/notifications/register'):
            return success_response(handle_push_token_registration(body))

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
    
    # Check for anomalies (edge score first, then optional cloud inference, then thresholds)
    anomaly_result = check_for_anomalies(
        data['metrics'],
        edge_score=edge_score,
        user_id=data['userId'],
        timestamp=data['timestamp']
    )
    anomaly_detected = anomaly_result['anomalyDetected']
    if anomaly_result.get('cloudScore') is not None:
        item['cloudAnomalyScore'] = convert_floats_to_decimal(anomaly_result['cloudScore'])
        item['cloudAnomalyDetected'] = bool(anomaly_result.get('cloudDetected', False))
    
    if anomaly_detected:
        # Update item with anomaly flag
        update_expression = ['anomalyDetected = :val']
        expression_values = {':val': True}

        if anomaly_result.get('cloudScore') is not None:
            update_expression.append('cloudAnomalyScore = :cloudScore')
            expression_values[':cloudScore'] = convert_floats_to_decimal(anomaly_result['cloudScore'])
        if anomaly_result.get('cloudDetected') is not None:
            update_expression.append('cloudAnomalyDetected = :cloudDetected')
            expression_values[':cloudDetected'] = bool(anomaly_result['cloudDetected'])

        table.update_item(
            Key={
                'userId': data['userId'],
                'timestamp': int(data['timestamp'])
            },
            UpdateExpression='SET ' + ', '.join(update_expression),
            ExpressionAttributeValues=expression_values
        )
        
        # Trigger notification (if needed)
        send_anomaly_notification({
            'userId': data['userId'],
            'timestamp': int(data['timestamp']),
            'metrics': data['metrics'],
            'anomalySource': anomaly_result.get('source', 'none')
        })
    
    return {
        'success': True,
        'message': 'Data ingested successfully',
        'anomalyDetected': anomaly_detected,
        'anomalySource': anomaly_result.get('source', 'none'),
        'cloudScore': anomaly_result.get('cloudScore')
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


def check_for_anomalies(metrics, edge_score=None, user_id=None, timestamp=None):
    """
    Hybrid anomaly detection: edge score -> cloud inference -> thresholds.
    Returns a dict with anomaly status and optional cloud score.
    """
    # If edge model provided a score, use it (>=0.5 anomalous)
    if edge_score is not None:
        try:
            score_f = float(edge_score)
            if score_f >= 0.5:
                logger.warning(f"Anomaly detected via edge score: {score_f}")
                return {
                    'anomalyDetected': True,
                    'source': 'edge',
                    'cloudScore': None,
                    'cloudDetected': None
                }
        except Exception:
            pass

    # Optional cloud inference
    if cloud_inference_function:
        cloud_result = invoke_cloud_inference(metrics, user_id, timestamp)
        if cloud_result is not None:
            if cloud_result.get('is_anomaly'):
                logger.warning("Anomaly detected via cloud inference")
                return {
                    'anomalyDetected': True,
                    'source': 'cloud',
                    'cloudScore': cloud_result.get('cloud_score'),
                    'cloudDetected': True
                }
            return {
                'anomalyDetected': False,
                'source': 'cloud',
                'cloudScore': cloud_result.get('cloud_score'),
                'cloudDetected': False
            }

    # Fallback: Simple threshold-based detection
    heart_rate = metrics.get('heartRate') or metrics.get('heart_rate')
    if heart_rate is not None:
        if heart_rate > 150 or heart_rate < 40:
            logger.warning(f"Anomaly detected: Heart rate {heart_rate} BPM")
            return {
                'anomalyDetected': True,
                'source': 'threshold',
                'cloudScore': None,
                'cloudDetected': None
            }

    return {
        'anomalyDetected': False,
        'source': 'none',
        'cloudScore': None,
        'cloudDetected': None
    }


def send_anomaly_notification(message):
    """
    Send notification for detected anomaly
    SNS publish if a topic ARN is configured.
    """
    logger.info(f"Anomaly notification payload: {message}")
    if not sns_topic_arn:
        return

    try:
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps(message),
            Subject='Health Alert'
        )
    except Exception as e:
        logger.error(f"Failed to publish SNS notification: {str(e)}")


def handle_push_token_registration(data):
    """
    Register Expo push token for a user.
    Expected body: {"userId": "...", "deviceId": "...", "expoPushToken": "...", "platform": "ios"}
    """
    required_fields = ['userId', 'expoPushToken']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    user_id = data['userId']
    device_id = data.get('deviceId', 'mobile')
    expo_push_token = data['expoPushToken']
    platform = data.get('platform', 'unknown')

    push_table.put_item(
        Item={
            'userId': user_id,
            'deviceId': device_id,
            'expoPushToken': expo_push_token,
            'platform': platform,
            'updatedAt': int(datetime.now().timestamp() * 1000)
        }
    )

    return {
        'success': True,
        'message': 'Push token registered',
        'userId': user_id,
        'deviceId': device_id
    }


def validate_api_key(api_key):
    """
    Validate API key
    Use API Gateway API key if configured; otherwise allow any non-empty key.
    If no expected key is set, assume API Gateway is handling authentication.
    """
    if expected_api_key:
        result = api_key == expected_api_key
        if not result:
            logger.warning(f"Key mismatch. Expected starts with: {expected_api_key[:5]}..., Got starts with: {api_key[:5] if api_key else 'empty'}...")
        return result
    # If no expected key, API Gateway is handling auth - just check non-empty
    return len(api_key) > 0


def invoke_cloud_inference(metrics, user_id, timestamp):
    """
    Invoke the cloud anomaly inference Lambda if configured.
    Returns {'is_anomaly': bool, 'cloud_score': float} or None on error.
    """
    try:
        heart_rate = metrics.get('heartRate') or metrics.get('heart_rate') or 0
        steps = metrics.get('steps') or 0
        calories = metrics.get('calories') or 0
        distance = metrics.get('distance') or 0

        payload = {
            'metrics': [
                {
                    'metric_id': f"{user_id}:{timestamp}",
                    'heart_rate': heart_rate,
                    'steps': steps,
                    'calories': calories,
                    'distance': distance
                }
            ]
        }

        response = lambda_client.invoke(
            FunctionName=cloud_inference_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload).encode('utf-8')
        )

        raw_body = response.get('Payload')
        if raw_body is None:
            return None

        response_payload = json.loads(raw_body.read().decode('utf-8'))
        if response_payload.get('statusCode') != 200:
            logger.warning(f"Cloud inference returned status {response_payload.get('statusCode')}")
            return None

        body = json.loads(response_payload.get('body', '{}'))
        results = body.get('results', [])
        if not results:
            return None

        first = results[0]
        return {
            'is_anomaly': bool(first.get('is_anomaly')),
            'cloud_score': first.get('cloud_score')
        }

    except Exception as e:
        logger.error(f"Cloud inference invocation failed: {str(e)}")
        return None


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
