#!/bin/bash

# AWS Lambda Deployment Script for Health Monitoring System
# Updated Feb 2026: Uses Random Forest model (F1=1.00) instead of Isolation Forest

set -e

# Disable AWS CLI pager
export AWS_PAGER=""

echo "🚀 Deploying Health Monitoring Cloud Backend..."

# Configuration
FUNCTION_NAME="HealthDataIngestion"
INFERENCE_FUNCTION_NAME="HealthAnomalyInference"
NOTIFY_FUNCTION_NAME="HealthSnsToExpo"
READ_FUNCTION_NAME="HealthReadMetrics"
RUNTIME="python3.9"
HANDLER="lambda_function.lambda_handler"
INFERENCE_HANDLER="lambda_inference_sklearn.lambda_handler"
NOTIFY_HANDLER="sns_to_expo.lambda_handler"
READ_HANDLER="lambda_read_metrics.lambda_handler"
ROLE_NAME="HealthMonitorLambdaRole"
TABLE_NAME="HealthMetrics"
PUSH_TOKEN_TABLE="HealthPushTokens"
REGION="ap-south-2"
MODEL_BUCKET="health-ml-models"

# Best model: RandomForest (F1=1.00, AUC=1.00) — updated Feb 2026
MODEL_KEY="randomforest/model.pkl"
SCALER_KEY="randomforest/scaler.pkl"
MODEL_LOCAL_PATH="../../MLPipeline/models/saved_models/best_anomaly_randomforest.pkl"
SCALER_LOCAL_PATH="../../MLPipeline/models/saved_models/best_anomaly_scaler.pkl"

# Fallback: Isolation Forest (legacy)
LEGACY_MODEL_LOCAL_PATH="../../MLPipeline/models/saved_models/isolation_forest.pkl"
LEGACY_SCALER_LOCAL_PATH="../../MLPipeline/models/saved_models/scaler.pkl"
LEGACY_MODEL_KEY="isolation_forest/model.pkl"
LEGACY_SCALER_KEY="isolation_forest/scaler.pkl"

SNS_TOPIC_NAME="health-alerts"
SMS_SUBSCRIPTION_NUMBER="+917702062828"
EXPO_ACCESS_TOKEN=""
LAYER_NAME="health-ml-deps"
LAYER_DIR="layer_build"
LAYER_ZIP="layer.zip"
ECR_REPO_NAME="health-inference-lambda"
API_NAME="HealthMonitorAPI"
API_KEY_NAME="HealthMonitorApiKey"
USAGE_PLAN_NAME="HealthMonitorUsagePlan"

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $ACCOUNT_ID"
echo "📋 Region: $REGION"

# ──────────────────────────────────────────────────────────────
# Step 1: DynamoDB Tables
# ──────────────────────────────────────────────────────────────
echo ""
echo "📊 Step 1: Creating DynamoDB tables..."
aws dynamodb create-table \
    --table-name $TABLE_NAME \
    --attribute-definitions \
        AttributeName=userId,AttributeType=S \
        AttributeName=timestamp,AttributeType=N \
    --key-schema \
        AttributeName=userId,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION \
    2>/dev/null || echo "  ✓ Table $TABLE_NAME already exists"

aws dynamodb wait table-exists --table-name $TABLE_NAME --region $REGION

aws dynamodb create-table \
    --table-name $PUSH_TOKEN_TABLE \
    --attribute-definitions \
        AttributeName=userId,AttributeType=S \
        AttributeName=deviceId,AttributeType=S \
    --key-schema \
        AttributeName=userId,KeyType=HASH \
        AttributeName=deviceId,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION \
    2>/dev/null || echo "  ✓ Table $PUSH_TOKEN_TABLE already exists"

aws dynamodb wait table-exists --table-name $PUSH_TOKEN_TABLE --region $REGION

# ──────────────────────────────────────────────────────────────
# Step 2: IAM Role
# ──────────────────────────────────────────────────────────────
echo ""
echo "🔐 Step 2: Creating IAM role..."
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://iam-policy.json \
    2>/dev/null || echo "  ✓ Role $ROLE_NAME already exists"

# Attach policies
POLICIES=(
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
    "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
)
for policy in "${POLICIES[@]}"; do
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn "$policy" 2>/dev/null || true
done

echo "⏳ Waiting for IAM role to propagate..."
sleep 10

# ──────────────────────────────────────────────────────────────
# Step 3: ECR Repository + Docker Image
# ──────────────────────────────────────────────────────────────
echo ""
echo "🐳 Step 3: Building inference container..."
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $REGION \
    2>/dev/null || echo "  ✓ ECR repository already exists"

ECR_URI=$(aws ecr describe-repositories \
    --repository-names $ECR_REPO_NAME \
    --region $REGION \
    --query 'repositories[0].repositoryUri' \
    --output text)
echo "  📦 ECR Repository: $ECR_URI"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

echo "  🔨 Building Docker image..."
docker build -f Dockerfile.inference -t $ECR_REPO_NAME:latest .

echo "  ⬆️  Pushing to ECR..."
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
docker push $ECR_URI:latest

# ──────────────────────────────────────────────────────────────
# Step 4: Package Lambda Functions
# ──────────────────────────────────────────────────────────────
echo ""
echo "📦 Step 4: Packaging Lambda functions..."
rm -f function.zip notify.zip read.zip
zip function.zip lambda_function.py
zip notify.zip sns_to_expo.py
zip read.zip lambda_read_metrics.py

# ──────────────────────────────────────────────────────────────
# Step 5: Upload ML Models to S3
# ──────────────────────────────────────────────────────────────
echo ""
echo "🧠 Step 5: Uploading ML models to S3..."
aws s3 mb s3://$MODEL_BUCKET --region $REGION 2>/dev/null || echo "  ✓ Bucket already exists"

# Upload Random Forest (best model)
if [[ -f "$MODEL_LOCAL_PATH" && -f "$SCALER_LOCAL_PATH" ]]; then
    echo "  Uploading Random Forest model (F1=1.00)..."
    aws s3 cp "$MODEL_LOCAL_PATH" "s3://$MODEL_BUCKET/$MODEL_KEY" --region "$REGION" || true
    aws s3 cp "$SCALER_LOCAL_PATH" "s3://$MODEL_BUCKET/$SCALER_KEY" --region "$REGION" || true
    echo "  ✓ Random Forest model uploaded to s3://$MODEL_BUCKET/randomforest/"
else
    echo "  ⚠️  Random Forest model not found at:"
    echo "     $MODEL_LOCAL_PATH"
    echo "     Run: cd ../../MLPipeline && source venv/bin/activate && python src/tests/comprehensive_ml_test.py"
fi

# Also upload legacy Isolation Forest if available
if [[ -f "$LEGACY_MODEL_LOCAL_PATH" && -f "$LEGACY_SCALER_LOCAL_PATH" ]]; then
    echo "  Uploading legacy Isolation Forest model (backup)..."
    aws s3 cp "$LEGACY_MODEL_LOCAL_PATH" "s3://$MODEL_BUCKET/$LEGACY_MODEL_KEY" --region "$REGION" || true
    aws s3 cp "$LEGACY_SCALER_LOCAL_PATH" "s3://$MODEL_BUCKET/$LEGACY_SCALER_KEY" --region "$REGION" || true
fi

echo "  📁 S3 model inventory:"
aws s3 ls s3://$MODEL_BUCKET/ --recursive --region "$REGION" 2>/dev/null || true

# ──────────────────────────────────────────────────────────────
# Step 6: Deploy Lambda Functions
# ──────────────────────────────────────────────────────────────
echo ""
echo "☁️  Step 6: Deploying Lambda functions..."
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# 6a: Data Ingestion Lambda
echo "  📤 HealthDataIngestion..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &>/dev/null; then
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://function.zip \
        --region $REGION > /dev/null
else
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler $HANDLER \
        --zip-file fileb://function.zip \
        --timeout 30 \
        --memory-size 512 \
        --environment "{\"Variables\":{\"TABLE_NAME\":\"$TABLE_NAME\",\"REGION\":\"$REGION\"}}" \
        --region $REGION > /dev/null
fi

# 6b: Anomaly Inference Lambda (Container Image)
echo "  📤 HealthAnomalyInference (container)..."
if aws lambda get-function --function-name $INFERENCE_FUNCTION_NAME --region $REGION &>/dev/null; then
    CURRENT_TYPE=$(aws lambda get-function --function-name $INFERENCE_FUNCTION_NAME --region $REGION --query 'Configuration.PackageType' --output text)
    if [[ "$CURRENT_TYPE" == "Zip" ]]; then
        echo "    Deleting Zip-type function to recreate as Container Image..."
        aws lambda delete-function --function-name $INFERENCE_FUNCTION_NAME --region $REGION
        sleep 5
    fi
fi

if aws lambda get-function --function-name $INFERENCE_FUNCTION_NAME --region $REGION &>/dev/null; then
    aws lambda update-function-code \
        --function-name $INFERENCE_FUNCTION_NAME \
        --image-uri $ECR_URI:latest \
        --region $REGION > /dev/null
else
    aws lambda create-function \
        --function-name $INFERENCE_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ECR_URI:latest \
        --role $ROLE_ARN \
        --timeout 30 \
        --memory-size 1024 \
        --environment "{\"Variables\":{\"MODEL_BUCKET\":\"$MODEL_BUCKET\",\"MODEL_KEY\":\"$MODEL_KEY\",\"SCALER_KEY\":\"$SCALER_KEY\"}}" \
        --region $REGION > /dev/null
fi

# 6c: SNS to Expo Lambda
echo "  📤 HealthSnsToExpo..."
if aws lambda get-function --function-name $NOTIFY_FUNCTION_NAME --region $REGION &>/dev/null; then
    aws lambda update-function-code \
        --function-name $NOTIFY_FUNCTION_NAME \
        --zip-file fileb://notify.zip \
        --region $REGION > /dev/null
else
    aws lambda create-function \
        --function-name $NOTIFY_FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler $NOTIFY_HANDLER \
        --zip-file fileb://notify.zip \
        --timeout 30 \
        --memory-size 256 \
        --environment "{\"Variables\":{\"PUSH_TOKEN_TABLE\":\"$PUSH_TOKEN_TABLE\",\"EXPO_ACCESS_TOKEN\":\"$EXPO_ACCESS_TOKEN\"}}" \
        --region $REGION > /dev/null
fi

# 6d: Read Metrics Lambda
echo "  📤 HealthReadMetrics..."
if aws lambda get-function --function-name $READ_FUNCTION_NAME --region $REGION &>/dev/null; then
    aws lambda update-function-code \
        --function-name $READ_FUNCTION_NAME \
        --zip-file fileb://read.zip \
        --region $REGION > /dev/null
else
    aws lambda create-function \
        --function-name $READ_FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler $READ_HANDLER \
        --zip-file fileb://read.zip \
        --timeout 30 \
        --memory-size 256 \
        --environment "{\"Variables\":{\"TABLE_NAME\":\"$TABLE_NAME\",\"REGION\":\"$REGION\"}}" \
        --region $REGION > /dev/null
fi

# ──────────────────────────────────────────────────────────────
# Step 7: API Gateway (reuse existing or create new)
# ──────────────────────────────────────────────────────────────
echo ""
echo "🌐 Step 7: Configuring API Gateway..."

# Check for existing API Gateway
API_ID=$(aws apigateway get-rest-apis \
    --query "items[?name=='${API_NAME}'] | sort_by(@, &createdDate) | [-1].id" \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -z "$API_ID" || "$API_ID" == "None" ]]; then
    echo "  Creating new API Gateway..."
    API_ID=$(aws apigateway create-rest-api \
        --name $API_NAME \
        --description "Health Monitoring System API (Random Forest ML)" \
        --region $REGION \
        --query 'id' \
        --output text)
else
    echo "  ✓ Reusing existing API Gateway: $API_ID"
fi

echo "  📝 API Gateway ID: $API_ID"

# Clean up any duplicate API Gateways (keep only the latest)
DUPLICATE_API_IDS=$(aws apigateway get-rest-apis \
    --query "items[?name=='${API_NAME}'] | sort_by(@, &createdDate) | [:-1].id" \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -n "$DUPLICATE_API_IDS" && "$DUPLICATE_API_IDS" != "None" ]]; then
    for dup_id in $DUPLICATE_API_IDS; do
        echo "  🗑️  Cleaning up duplicate API Gateway: $dup_id"
        aws apigateway delete-rest-api --rest-api-id "$dup_id" --region $REGION 2>/dev/null || true
    done
fi

# Get root resource
ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query 'items[?path==`/`].id' \
    --output text \
    --region $REGION)

# Helper function to create or get resource
create_or_get_resource() {
    local parent_id=$1
    local path_part=$2
    local full_path=$3

    local resource_id=$(aws apigateway get-resources \
        --rest-api-id $API_ID \
        --query "items[?path=='${full_path}'].id" \
        --output text \
        --region $REGION 2>/dev/null || true)

    if [[ -z "$resource_id" || "$resource_id" == "None" ]]; then
        resource_id=$(aws apigateway create-resource \
            --rest-api-id $API_ID \
            --parent-id $parent_id \
            --path-part $path_part \
            --region $REGION \
            --query 'id' \
            --output text)
    fi
    echo "$resource_id"
}

# Create all resources
HEALTH_DATA_ID=$(create_or_get_resource "$ROOT_ID" "health-data" "/health-data")
INGEST_ID=$(create_or_get_resource "$HEALTH_DATA_ID" "ingest" "/health-data/ingest")
SYNC_ID=$(create_or_get_resource "$HEALTH_DATA_ID" "sync" "/health-data/sync")
HISTORY_ID=$(create_or_get_resource "$HEALTH_DATA_ID" "history" "/health-data/history")
HEALTH_ID=$(create_or_get_resource "$ROOT_ID" "health" "/health")
METRICS_ID=$(create_or_get_resource "$HEALTH_ID" "metrics" "/health/metrics")
NOTIFY_PARENT_ID=$(create_or_get_resource "$ROOT_ID" "notifications" "/notifications")
REGISTER_ID=$(create_or_get_resource "$NOTIFY_PARENT_ID" "register" "/notifications/register")

# Helper: create method + integration
setup_method() {
    local resource_id=$1
    local http_method=$2
    local function_name=$3

    aws apigateway put-method \
        --rest-api-id $API_ID \
        --resource-id $resource_id \
        --http-method $http_method \
        --authorization-type NONE \
        --api-key-required \
        --region $REGION \
        2>/dev/null || true

    aws apigateway put-integration \
        --rest-api-id $API_ID \
        --resource-id $resource_id \
        --http-method $http_method \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$function_name/invocations" \
        --region $REGION \
        2>/dev/null || true
}

# Setup all routes
echo "  Setting up API routes..."
setup_method "$INGEST_ID" "POST" "$FUNCTION_NAME"
setup_method "$SYNC_ID" "POST" "$FUNCTION_NAME"
setup_method "$SYNC_ID" "GET" "$READ_FUNCTION_NAME"
setup_method "$HISTORY_ID" "GET" "$READ_FUNCTION_NAME"
setup_method "$HEALTH_ID" "GET" "$READ_FUNCTION_NAME"
setup_method "$METRICS_ID" "GET" "$READ_FUNCTION_NAME"
setup_method "$REGISTER_ID" "POST" "$FUNCTION_NAME"

# Deploy API
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --region $REGION > /dev/null

# ──────────────────────────────────────────────────────────────
# Step 8: SNS Topic
# ──────────────────────────────────────────────────────────────
echo ""
echo "📣 Step 8: Setting up SNS..."
SNS_TOPIC_ARN=$(aws sns create-topic \
    --name $SNS_TOPIC_NAME \
    --region $REGION \
    --query 'TopicArn' \
    --output text)

aws lambda add-permission \
    --function-name $NOTIFY_FUNCTION_NAME \
    --statement-id sns-invoke \
    --action lambda:InvokeFunction \
    --principal sns.amazonaws.com \
    --source-arn "$SNS_TOPIC_ARN" \
    --region $REGION \
    2>/dev/null || true

aws sns subscribe \
    --topic-arn "$SNS_TOPIC_ARN" \
    --protocol lambda \
    --notification-endpoint "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$NOTIFY_FUNCTION_NAME" \
    --region "$REGION" \
    2>/dev/null || true

if [[ -n "$SMS_SUBSCRIPTION_NUMBER" ]]; then
    aws sns subscribe \
        --topic-arn "$SNS_TOPIC_ARN" \
        --protocol sms \
        --notification-endpoint "$SMS_SUBSCRIPTION_NUMBER" \
        --region "$REGION" \
        2>/dev/null || true
fi

# ──────────────────────────────────────────────────────────────
# Step 9: API Key + Usage Plan
# ──────────────────────────────────────────────────────────────
echo ""
echo "🔑 Step 9: Setting up API key..."

API_KEY_ID=$(aws apigateway get-api-keys \
    --query "items[?name=='${API_KEY_NAME}'].id | [0]" \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -z "$API_KEY_ID" || "$API_KEY_ID" == "None" ]]; then
    API_KEY_ID=$(aws apigateway create-api-key \
        --name $API_KEY_NAME \
        --enabled \
        --region $REGION \
        --query 'id' \
        --output text)
fi

API_KEY_VALUE=$(aws apigateway get-api-key \
    --api-key $API_KEY_ID \
    --include-value \
    --query 'value' \
    --output text \
    --region $REGION)

USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
    --query "items[?name=='${USAGE_PLAN_NAME}'].id | [0]" \
    --output text \
    --region $REGION 2>/dev/null || true)

if [[ -z "$USAGE_PLAN_ID" || "$USAGE_PLAN_ID" == "None" ]]; then
    USAGE_PLAN_ID=$(aws apigateway create-usage-plan \
        --name $USAGE_PLAN_NAME \
        --api-stages apiId=$API_ID,stage=prod \
        --region $REGION \
        --query 'id' \
        --output text)
fi

aws apigateway create-usage-plan-key \
    --usage-plan-id $USAGE_PLAN_ID \
    --key-id $API_KEY_ID \
    --key-type API_KEY \
    --region $REGION \
    2>/dev/null || true

# ──────────────────────────────────────────────────────────────
# Step 10: Update Lambda Environment Variables
# ──────────────────────────────────────────────────────────────
echo ""
echo "⚙️  Step 10: Updating Lambda environment variables..."

# Wait for any pending updates
sleep 5

aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment "{\"Variables\":{\"TABLE_NAME\":\"$TABLE_NAME\",\"PUSH_TOKEN_TABLE\":\"$PUSH_TOKEN_TABLE\",\"REGION\":\"$REGION\",\"API_KEY\":\"$API_KEY_VALUE\",\"SNS_TOPIC_ARN\":\"$SNS_TOPIC_ARN\",\"CLOUD_INFERENCE_FUNCTION\":\"$INFERENCE_FUNCTION_NAME\"}}" \
    --region $REGION > /dev/null

aws lambda update-function-configuration \
    --function-name $READ_FUNCTION_NAME \
    --environment "{\"Variables\":{\"TABLE_NAME\":\"$TABLE_NAME\",\"REGION\":\"$REGION\",\"API_KEY\":\"$API_KEY_VALUE\"}}" \
    --region $REGION > /dev/null

# Update inference Lambda to use Random Forest model
sleep 5
aws lambda update-function-configuration \
    --function-name $INFERENCE_FUNCTION_NAME \
    --environment "{\"Variables\":{\"MODEL_BUCKET\":\"$MODEL_BUCKET\",\"MODEL_KEY\":\"$MODEL_KEY\",\"SCALER_KEY\":\"$SCALER_KEY\"}}" \
    --region $REGION > /dev/null

# Add API Gateway invoke permissions
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*" \
    --region $REGION \
    2>/dev/null || true

aws lambda add-permission \
    --function-name $READ_FUNCTION_NAME \
    --statement-id apigateway-invoke-read \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*" \
    --region $REGION \
    2>/dev/null || true

# ──────────────────────────────────────────────────────────────
# Output
# ──────────────────────────────────────────────────────────────
API_BASE="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"

echo ""
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 API Endpoints:"
echo "   POST ${API_BASE}/health-data/ingest"
echo "   POST ${API_BASE}/health-data/sync"
echo "   GET  ${API_BASE}/health-data/sync"
echo "   GET  ${API_BASE}/health-data/history"
echo "   GET  ${API_BASE}/health/metrics"
echo "   GET  ${API_BASE}/health"
echo "   POST ${API_BASE}/notifications/register"
echo ""
echo "🔐 API Key: $API_KEY_VALUE"
echo ""
echo "⚡ Lambda Functions:"
echo "   $FUNCTION_NAME (Zip, 512MB)"
echo "   $INFERENCE_FUNCTION_NAME (Container, 1024MB)"
echo "   $NOTIFY_FUNCTION_NAME (Zip, 256MB)"
echo "   $READ_FUNCTION_NAME (Zip, 256MB)"
echo ""
echo "🧠 ML Model: Random Forest (F1=1.00)"
echo "   S3: s3://$MODEL_BUCKET/$MODEL_KEY"
echo "   Scaler: s3://$MODEL_BUCKET/$SCALER_KEY"
echo ""
echo "📊 DynamoDB: $TABLE_NAME, $PUSH_TOKEN_TABLE"
echo "📣 SNS: $SNS_TOPIC_ARN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔧 Next Steps:"
echo "1. Update WearOSApp ApiConfig.kt:"
echo "   const val BASE_URL = \"${API_BASE}/\""
echo "   const val API_KEY = \"$API_KEY_VALUE\""
echo ""
echo "2. Test the endpoint:"
echo "   curl -X POST ${API_BASE}/health-data/ingest \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -H 'X-API-Key: $API_KEY_VALUE' \\"
echo "     -d @test-payload.json"
echo ""

# Cleanup
rm -rf package function.zip notify.zip read.zip
