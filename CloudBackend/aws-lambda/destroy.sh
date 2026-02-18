#!/bin/bash

# AWS Lambda Teardown Script for Health Monitoring System

set -e

echo "🧹 Destroying Health Monitoring Cloud Backend..."

# Configuration (match deploy.sh)
FUNCTION_NAME="HealthDataIngestion"
INFERENCE_FUNCTION_NAME="HealthAnomalyInference"
NOTIFY_FUNCTION_NAME="HealthSnsToExpo"
ROLE_NAME="HealthMonitorLambdaRole"
TABLE_NAME="HealthMetrics"
PUSH_TOKEN_TABLE="HealthPushTokens"
REGION="ap-south-2"
MODEL_BUCKET="health-ml-models"
MODEL_KEY="isolation_forest/model.pkl"
SCALER_KEY="isolation_forest/scaler.pkl"
SNS_TOPIC_NAME="health-alerts"
API_NAME="HealthMonitorAPI"
API_KEY_NAME="HealthMonitorApiKey"
USAGE_PLAN_NAME="HealthMonitorUsagePlan"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "📋 AWS Account ID: $ACCOUNT_ID"

# Delete API Gateway
API_ID=$(aws apigateway get-rest-apis \
    --query "items[?name=='${API_NAME}'].id" \
    --output text \
    --region $REGION || true)

if [[ -n "$API_ID" && "$API_ID" != "None" ]]; then
    echo "🗑️  Deleting API Gateway $API_ID..."
    aws apigateway delete-rest-api --rest-api-id "$API_ID" --region $REGION || true
fi

# Delete usage plan and API key
USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
    --query "items[?name=='${USAGE_PLAN_NAME}'].id" \
    --output text \
    --region $REGION || true)

API_KEY_ID=$(aws apigateway get-api-keys \
    --query "items[?name=='${API_KEY_NAME}'].id" \
    --output text \
    --region $REGION || true)

if [[ -n "$USAGE_PLAN_ID" && "$USAGE_PLAN_ID" != "None" ]]; then
    echo "🗑️  Deleting usage plan $USAGE_PLAN_ID..."
    aws apigateway delete-usage-plan --usage-plan-id "$USAGE_PLAN_ID" --region $REGION || true
fi

if [[ -n "$API_KEY_ID" && "$API_KEY_ID" != "None" ]]; then
    echo "🗑️  Deleting API key $API_KEY_ID..."
    aws apigateway delete-api-key --api-key "$API_KEY_ID" --region $REGION || true
fi

# Delete Lambda functions
for fn in "$FUNCTION_NAME" "$INFERENCE_FUNCTION_NAME" "$NOTIFY_FUNCTION_NAME"; do
    echo "🗑️  Deleting Lambda function $fn..."
    aws lambda delete-function --function-name "$fn" --region $REGION || true
done

# Delete SNS topic
SNS_TOPIC_ARN=$(aws sns list-topics \
    --query "Topics[?contains(TopicArn, ':${SNS_TOPIC_NAME}')].TopicArn" \
    --output text \
    --region $REGION || true)

if [[ -n "$SNS_TOPIC_ARN" && "$SNS_TOPIC_ARN" != "None" ]]; then
    echo "🗑️  Deleting SNS topic $SNS_TOPIC_ARN..."
    aws sns delete-topic --topic-arn "$SNS_TOPIC_ARN" --region $REGION || true
fi

# Delete DynamoDB tables
for table in "$TABLE_NAME" "$PUSH_TOKEN_TABLE"; do
    echo "🗑️  Deleting DynamoDB table $table..."
    aws dynamodb delete-table --table-name "$table" --region $REGION || true
done

# Remove model artifacts from S3 (objects only, not the bucket)
if [[ -n "$MODEL_BUCKET" ]]; then
    echo "🗑️  Deleting S3 objects..."
    aws s3 rm "s3://$MODEL_BUCKET/$MODEL_KEY" --region $REGION || true
    aws s3 rm "s3://$MODEL_BUCKET/$SCALER_KEY" --region $REGION || true
fi

# Detach policies and delete IAM role
POLICIES=(
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
    "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
)

echo "🗑️  Detaching IAM policies and deleting role..."
for policy in "${POLICIES[@]}"; do
    aws iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn "$policy" || true
done
aws iam delete-role --role-name "$ROLE_NAME" || true

echo "✅ Destroy complete."
