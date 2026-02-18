import json
import boto3
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'HealthMetrics')
table = dynamodb.Table(table_name)
expected_api_key = os.environ.get('API_KEY', '').strip()

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-API-Key',
    'Access-Control-Allow-Methods': 'GET,OPTIONS'
}


def lambda_handler(event, context):
    """
    Lambda handler for reading health metrics from DynamoDB
    """
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': ''
            }

        # Validate API key
        headers = event.get('headers', {})
        api_key = headers.get('X-API-Key') or headers.get('x-api-key') or ''
        if not validate_api_key(api_key):
            logger.warning(f"API key validation failed. Headers: {list(headers.keys())}")
            return error_response(401, 'Unauthorized: Invalid API key')

        # Get path and query parameters
        path = event.get('path', '')
        query_params = event.get('queryStringParameters') or {}
        
        # Route to appropriate handler
        if path.endswith('/health-data/history'):
            return handle_get_history(query_params)
        elif path.endswith('/health/metrics'):
            return handle_get_metrics(query_params)
        else:
            return error_response(404, 'Not found')

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return error_response(500, f'Internal server error: {str(e)}')


def handle_get_metrics(query_params):
    """
    Get metrics for a specific user
    Query params: userId (required), limit (optional, default 100)
    """
    user_id = query_params.get('userId') if query_params else None
    if not user_id:
        return error_response(400, 'Missing required parameter: userId')

    try:
        limit = int(query_params.get('limit', 100)) if query_params else 100
        limit = min(limit, 1000)  # Cap at 1000
    except ValueError:
        return error_response(400, 'Invalid limit parameter')

    try:
        # Query metrics for user
        response = table.query(
            KeyConditionExpression='userId = :userId',
            ExpressionAttributeValues={
                ':userId': user_id
            },
            Limit=limit,
            ScanIndexForward=False  # Sort by timestamp descending (most recent first)
        )

        items = response.get('Items', [])
        metrics = []

        for item in items:
            # Handle both nested and flat metric structures
            metrics_data = item.get('metrics', {}) if isinstance(item.get('metrics'), dict) else {}
            
            metric = {
                'id': f"{item['userId']}:{int(item['timestamp'])}",
                'timestamp': datetime.fromtimestamp(int(item['timestamp'])).isoformat(),
                'heartRate': float(item.get('heartRate', metrics_data.get('heartRate', 0))),
                'steps': int(item.get('steps', metrics_data.get('steps', 0))),
                'calories': float(item.get('calories', metrics_data.get('calories', 0))),
                'distance': float(item.get('distance', metrics_data.get('distance', 0))),
                'isAnomaly': item.get('isAnomaly', item.get('anomalyDetected', False)),
                'anomalyScore': float(item.get('anomalyScore', item.get('cloudAnomalyScore', item.get('edgeAnomalyScore', 0)))),
            }
            metrics.append(metric)

        logger.info(f"Retrieved {len(metrics)} metrics for user {user_id}")
        return success_response({
            'success': True,
            'metrics': metrics,
            'count': len(metrics),
            'userId': user_id
        })

    except Exception as e:
        logger.error(f"Error querying metrics: {str(e)}", exc_info=True)
        return error_response(500, f'Failed to retrieve metrics: {str(e)}')


def handle_get_history(query_params):
    """
    Get metrics history for a user within a date range
    Query params: userId (required), startDate (optional), endDate (optional), limit (optional, default 100)
    Dates should be ISO format (e.g., 2024-01-15T00:00:00Z)
    """
    user_id = query_params.get('userId') if query_params else None
    if not user_id:
        return error_response(400, 'Missing required parameter: userId')

    try:
        limit = int(query_params.get('limit', 100)) if query_params else 100
        limit = min(limit, 1000)  # Cap at 1000
    except ValueError:
        return error_response(400, 'Invalid limit parameter')

    # Parse date range
    start_timestamp = None
    end_timestamp = None

    try:
        if query_params and query_params.get('startDate'):
            start_date = datetime.fromisoformat(query_params.get('startDate').replace('Z', '+00:00'))
            start_timestamp = int(start_date.timestamp() * 1000)

        if query_params and query_params.get('endDate'):
            end_date = datetime.fromisoformat(query_params.get('endDate').replace('Z', '+00:00'))
            end_timestamp = int(end_date.timestamp() * 1000)
    except ValueError as e:
        return error_response(400, f'Invalid date format: {str(e)}. Use ISO format (e.g., 2024-01-15T00:00:00Z)')

    try:
        # Build query
        key_condition = 'userId = :userId'
        expression_values = {':userId': user_id}

        if start_timestamp and end_timestamp:
            key_condition += ' AND #ts BETWEEN :start AND :end'
            expression_values[':start'] = start_timestamp
            expression_values[':end'] = end_timestamp
        elif start_timestamp:
            key_condition += ' AND #ts >= :start'
            expression_values[':start'] = start_timestamp
        elif end_timestamp:
            key_condition += ' AND #ts <= :end'
            expression_values[':end'] = end_timestamp

        response = table.query(
            KeyConditionExpression=key_condition,
            ExpressionAttributeNames={'#ts': 'timestamp'} if start_timestamp or end_timestamp else None,
            ExpressionAttributeValues=expression_values,
            Limit=limit,
            ScanIndexForward=False  # Sort by timestamp descending
        )

        items = response.get('Items', [])
        metrics = []

        for item in items:
            # Handle both nested and flat metric structures
            metrics_data = item.get('metrics', {}) if isinstance(item.get('metrics'), dict) else {}
            
            metric = {
                'id': f"{item['userId']}:{int(item['timestamp'])}",
                'timestamp': datetime.fromtimestamp(int(item['timestamp'])).isoformat(),
                'heartRate': float(item.get('heartRate', metrics_data.get('heartRate', 0))),
                'steps': int(item.get('steps', metrics_data.get('steps', 0))),
                'calories': float(item.get('calories', metrics_data.get('calories', 0))),
                'distance': float(item.get('distance', metrics_data.get('distance', 0))),
                'isAnomaly': item.get('isAnomaly', item.get('anomalyDetected', False)),
                'anomalyScore': float(item.get('anomalyScore', item.get('cloudAnomalyScore', item.get('edgeAnomalyScore', 0)))),
            }
            metrics.append(metric)

        logger.info(f"Retrieved {len(metrics)} history metrics for user {user_id}")
        return success_response({
            'success': True,
            'metrics': metrics,
            'count': len(metrics),
            'userId': user_id,
            'startDate': query_params.get('startDate') if query_params else None,
            'endDate': query_params.get('endDate') if query_params else None
        })

    except Exception as e:
        logger.error(f"Error querying history: {str(e)}", exc_info=True)
        return error_response(500, f'Failed to retrieve history: {str(e)}')


def validate_api_key(api_key):
    """
    Validate API key
    """
    if expected_api_key:
        result = api_key == expected_api_key
        if not result:
            logger.warning(f"Key mismatch. Expected starts with: {expected_api_key[:5]}..., Got starts with: {api_key[:5] if api_key else 'empty'}...")
        return result
    return len(api_key) > 0


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
