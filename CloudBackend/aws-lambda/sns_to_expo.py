import json
import logging
import os
import urllib.request
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
PUSH_TOKEN_TABLE = os.environ.get("PUSH_TOKEN_TABLE", "HealthPushTokens")
EXPO_ACCESS_TOKEN = os.environ.get("EXPO_ACCESS_TOKEN", "").strip()


dynamodb = boto3.resource("dynamodb")
push_table = dynamodb.Table(PUSH_TOKEN_TABLE)


def lambda_handler(event, context):
    try:
        records = event.get("Records", [])
        for record in records:
            sns_message = record.get("Sns", {}).get("Message", "")
            payload = parse_message(sns_message)
            if not payload:
                continue

            user_id = payload.get("userId")
            if not user_id:
                logger.warning("SNS message missing userId; skipping")
                continue

            tokens = get_push_tokens(user_id)
            if not tokens:
                logger.info(f"No push tokens for user {user_id}")
                continue

            send_expo_push(tokens, payload)

        return {"statusCode": 200, "body": "ok"}
    except Exception as e:
        logger.error(f"SNS to Expo handler failed: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": "error"}


def parse_message(message):
    try:
        return json.loads(message)
    except Exception:
        return {"message": message}


def get_push_tokens(user_id):
    try:
        response = push_table.query(
            KeyConditionExpression=Key("userId").eq(user_id)
        )
        items = response.get("Items", [])
        return [item.get("expoPushToken") for item in items if item.get("expoPushToken")]
    except Exception as e:
        logger.error(f"Failed to query push tokens: {str(e)}")
        return []


def send_expo_push(tokens, payload):
    messages = []
    # Build a descriptive push body from anomaly reasons if available
    anomaly_reasons = payload.get("anomalyReasons", [])
    if anomaly_reasons:
        body_text = anomaly_reasons[0]  # Lead with the most important reason
        if len(anomaly_reasons) > 1:
            body_text += f" (+{len(anomaly_reasons) - 1} more)"
    else:
        body_text = "An anomaly was detected. Open the app for details."

    for token in tokens:
        messages.append({
            "to": token,
            "sound": "default",
            "title": "Health Alert",
            "body": body_text,
            "data": payload
        })

    body = json.dumps(messages).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    if EXPO_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {EXPO_ACCESS_TOKEN}"

    request = urllib.request.Request(EXPO_PUSH_URL, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            logger.info(f"Expo response: {response.status} {response_body}")
    except Exception as e:
        logger.error(f"Failed to send Expo push: {str(e)}")
