#!/bin/bash

# AWS Lambda Teardown Script for Health Monitoring System
# Destroys ALL resources created by deploy.sh
# Updated Feb 2026: Handles Random Forest model, duplicate API Gateways

set -e

# Disable AWS CLI pager
export AWS_PAGER=""

echo "🧹 Destroying Health Monitoring Cloud Backend..."
echo ""

# Configuration (must match deploy.sh)
FUNCTION_NAME="HealthDataIngestion"
INFERENCE_FUNCTION_NAME="HealthAnomalyInference"
NOTIFY_FUNCTION_NAME="HealthSnsToExpo"
READ_FUNCTION_NAME="HealthReadMetrics"
ROLE_NAME="HealthMonitorLambdaRole"
TABLE_NAME="HealthMetrics"
PUSH_TOKEN_TABLE="HealthPushTokens"
REGION="ap-south-2"
MODEL_BUCKET="health-ml-models"
SNS_TOPIC_NAME="health-alerts"
LAYER_NAME="health-ml-deps"
ECR_REPO_NAME="health-inference-lambda"
API_NAME="HealthMonitorAPI"
API_KEY_NAME="HealthMonitorApiKey"
USAGE_PLAN_NAME="HealthMonitorUsagePlan"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $ACCOUNT_ID"
echo "📋 Region: $REGION"
echo ""

# ──────────────────────────────────────────────────────────────
# Step 1: Delete ALL API Gateways with matching name
# ──────────────────────────────────────────────────────────────
echo "🗑️  Step 1: Deleting API Gateways..."
ALL_API_IDS=$(aws apigateway get-rest-apis \
    --query "items[?name=='${API_NAME}'].id" \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -n "$ALL_API_IDS" && "$ALL_API_IDS" != "None" ]]; then
    for api_id in $ALL_API_IDS; do
        echo "  Deleting API Gateway: $api_id"
        aws apigateway delete-rest-api --rest-api-id "$api_id" --region $REGION 2>/dev/null || true
    done
else
    echo "  No API Gateways found"
fi

# ──────────────────────────────────────────────────────────────
# Step 2: Delete Usage Plans and API Keys
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 2: Deleting usage plans and API keys..."

# Delete all usage plans with matching name
USAGE_PLAN_IDS=$(aws apigateway get-usage-plans \
    --query "items[?name=='${USAGE_PLAN_NAME}'].id" \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -n "$USAGE_PLAN_IDS" && "$USAGE_PLAN_IDS" != "None" ]]; then
    for plan_id in $USAGE_PLAN_IDS; do
        # Delete usage plan keys first
        USAGE_PLAN_KEYS=$(aws apigateway get-usage-plan-keys \
            --usage-plan-id "$plan_id" \
            --query 'items[*].id' \
            --output text \
            --region $REGION 2>/dev/null || true)

        if [[ -n "$USAGE_PLAN_KEYS" && "$USAGE_PLAN_KEYS" != "None" ]]; then
            for key_id in $USAGE_PLAN_KEYS; do
                aws apigateway delete-usage-plan-key \
                    --usage-plan-id "$plan_id" \
                    --key-id "$key_id" \
                    --region $REGION 2>/dev/null || true
            done
        fi

        echo "  Deleting usage plan: $plan_id"
        aws apigateway delete-usage-plan --usage-plan-id "$plan_id" --region $REGION 2>/dev/null || true
    done
fi

# Delete all API keys with matching name
API_KEY_IDS=$(aws apigateway get-api-keys \
    --query "items[?name=='${API_KEY_NAME}'].id" \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -n "$API_KEY_IDS" && "$API_KEY_IDS" != "None" ]]; then
    for key_id in $API_KEY_IDS; do
        echo "  Deleting API key: $key_id"
        aws apigateway delete-api-key --api-key "$key_id" --region $REGION 2>/dev/null || true
    done
fi

# ──────────────────────────────────────────────────────────────
# Step 3: Remove Lambda Permissions
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 3: Removing Lambda permissions..."
aws lambda remove-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id apigateway-invoke \
    --region $REGION 2>/dev/null || true

aws lambda remove-permission \
    --function-name "$NOTIFY_FUNCTION_NAME" \
    --statement-id sns-invoke \
    --region $REGION 2>/dev/null || true

aws lambda remove-permission \
    --function-name "$READ_FUNCTION_NAME" \
    --statement-id apigateway-invoke-read \
    --region $REGION 2>/dev/null || true

# ──────────────────────────────────────────────────────────────
# Step 4: Delete Lambda Functions
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 4: Deleting Lambda functions..."
for fn in "$FUNCTION_NAME" "$INFERENCE_FUNCTION_NAME" "$NOTIFY_FUNCTION_NAME" "$READ_FUNCTION_NAME"; do
    if aws lambda get-function --function-name "$fn" --region $REGION &>/dev/null; then
        echo "  Deleting: $fn"
        aws lambda delete-function --function-name "$fn" --region $REGION || true
    else
        echo "  Not found: $fn"
    fi
done

# ──────────────────────────────────────────────────────────────
# Step 5: Delete CloudWatch Log Groups
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 5: Deleting CloudWatch log groups..."
for lg in "/aws/lambda/$FUNCTION_NAME" "/aws/lambda/$INFERENCE_FUNCTION_NAME" "/aws/lambda/$NOTIFY_FUNCTION_NAME" "/aws/lambda/$READ_FUNCTION_NAME"; do
    aws logs delete-log-group --log-group-name "$lg" --region $REGION 2>/dev/null || true
    echo "  Deleted: $lg"
done

# ──────────────────────────────────────────────────────────────
# Step 6: Delete Lambda Layer Versions
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 6: Deleting Lambda layer versions..."
LAYER_VERSIONS=$(aws lambda list-layer-versions \
    --layer-name "$LAYER_NAME" \
    --query 'LayerVersions[*].Version' \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -n "$LAYER_VERSIONS" && "$LAYER_VERSIONS" != "None" ]]; then
    for version in $LAYER_VERSIONS; do
        echo "  Deleting layer version: $version"
        aws lambda delete-layer-version \
            --layer-name "$LAYER_NAME" \
            --version-number "$version" \
            --region $REGION || true
    done
else
    echo "  No layer versions found"
fi

# ──────────────────────────────────────────────────────────────
# Step 7: Delete ECR Repository
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 7: Deleting ECR repository..."
if aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region $REGION &>/dev/null; then
    aws ecr delete-repository \
        --repository-name "$ECR_REPO_NAME" \
        --force \
        --region $REGION > /dev/null
    echo "  Deleted: $ECR_REPO_NAME"
else
    echo "  Not found: $ECR_REPO_NAME"
fi

# ──────────────────────────────────────────────────────────────
# Step 8: Delete SNS Topic + Subscriptions
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 8: Deleting SNS topic..."
SNS_TOPIC_ARN=$(aws sns list-topics \
    --query "Topics[?contains(TopicArn, ':${SNS_TOPIC_NAME}')].TopicArn | [0]" \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -n "$SNS_TOPIC_ARN" && "$SNS_TOPIC_ARN" != "None" ]]; then
    # Delete subscriptions first
    SUBSCRIPTIONS=$(aws sns list-subscriptions-by-topic \
        --topic-arn "$SNS_TOPIC_ARN" \
        --query 'Subscriptions[*].SubscriptionArn' \
        --output text \
        --region $REGION 2>/dev/null || true)

    if [[ -n "$SUBSCRIPTIONS" && "$SUBSCRIPTIONS" != "None" ]]; then
        for sub in $SUBSCRIPTIONS; do
            if [[ "$sub" != "PendingConfirmation" ]]; then
                aws sns unsubscribe --subscription-arn "$sub" --region $REGION 2>/dev/null || true
            fi
        done
    fi

    echo "  Deleting topic: $SNS_TOPIC_ARN"
    aws sns delete-topic --topic-arn "$SNS_TOPIC_ARN" --region $REGION || true
else
    echo "  No SNS topic found"
fi

# ──────────────────────────────────────────────────────────────
# Step 9: Delete DynamoDB Tables
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 9: Deleting DynamoDB tables..."
for table in "$TABLE_NAME" "$PUSH_TOKEN_TABLE"; do
    if aws dynamodb describe-table --table-name "$table" --region $REGION &>/dev/null; then
        echo "  Deleting: $table"
        aws dynamodb delete-table --table-name "$table" --region $REGION > /dev/null || true
    else
        echo "  Not found: $table"
    fi
done

# ──────────────────────────────────────────────────────────────
# Step 10: Delete S3 Bucket (model artifacts)
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 10: Deleting S3 bucket..."
if aws s3 ls "s3://$MODEL_BUCKET" &>/dev/null; then
    echo "  Emptying bucket contents..."
    aws s3 rm "s3://$MODEL_BUCKET" --recursive --region $REGION 2>/dev/null || true
    echo "  Deleting bucket: $MODEL_BUCKET"
    aws s3 rb "s3://$MODEL_BUCKET" --region $REGION 2>/dev/null || true
else
    echo "  Bucket not found: $MODEL_BUCKET"
fi

# ──────────────────────────────────────────────────────────────
# Step 11: Detach Policies and Delete IAM Role
# ──────────────────────────────────────────────────────────────
echo ""
echo "🗑️  Step 11: Deleting IAM role..."
if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
    POLICIES=(
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
        "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
        "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
    )
    for policy in "${POLICIES[@]}"; do
        aws iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn "$policy" 2>/dev/null || true
    done
    aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null || true
    echo "  Deleted: $ROLE_NAME"
else
    echo "  Not found: $ROLE_NAME"
fi

# ──────────────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────────────
echo ""
echo "✅ Destroy complete!"
echo ""
echo "Resources removed:"
echo "  • Lambda: $FUNCTION_NAME, $INFERENCE_FUNCTION_NAME, $NOTIFY_FUNCTION_NAME, $READ_FUNCTION_NAME"
echo "  • DynamoDB: $TABLE_NAME, $PUSH_TOKEN_TABLE"
echo "  • API Gateway: $API_NAME (all instances)"
echo "  • S3: $MODEL_BUCKET (including randomforest/ and isolation_forest/ models)"
echo "  • SNS: $SNS_TOPIC_NAME"
echo "  • ECR: $ECR_REPO_NAME"
echo "  • IAM Role: $ROLE_NAME"
echo "  • CloudWatch Logs: all Lambda log groups"
