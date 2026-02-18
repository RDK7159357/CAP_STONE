#!/bin/bash

# AWS Lambda Deployment Script for Health Monitoring System

set -e

# Disable AWS CLI pager
export AWS_PAGER=""

echo "🚀 Deploying Health Monitoring Cloud Backend..."

# Configuration
FUNCTION_NAME="HealthDataIngestion"
INFERENCE_FUNCTION_NAME="HealthAnomalyInference"
NOTIFY_FUNCTION_NAME="HealthSnsToExpo"
RUNTIME="python3.9"
HANDLER="lambda_function.lambda_handler"
INFERENCE_HANDLER="lambda_inference_sklearn.lambda_handler"
NOTIFY_HANDLER="sns_to_expo.lambda_handler"
ROLE_NAME="HealthMonitorLambdaRole"
TABLE_NAME="HealthMetrics"
PUSH_TOKEN_TABLE="HealthPushTokens"
REGION="ap-south-2"
MODEL_BUCKET="health-ml-models"
MODEL_KEY="isolation_forest/model.pkl"
SCALER_KEY="isolation_forest/scaler.pkl"
MODEL_LOCAL_PATH="../../MLPipeline/models/saved_models/isolation_forest.pkl"
SCALER_LOCAL_PATH="../../MLPipeline/models/saved_models/scaler.pkl"
SNS_TOPIC_NAME="health-alerts"
SMS_SUBSCRIPTION_NUMBER="+917702062828"
EXPO_ACCESS_TOKEN=""
LAYER_NAME="health-ml-deps"
LAYER_DIR="layer_build"
LAYER_ZIP="layer.zip"

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $ACCOUNT_ID"

# Step 1: Create DynamoDB Table
echo "📊 Creating DynamoDB table..."
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
    2>/dev/null || echo "Table already exists"

# Wait for table to be active
echo "⏳ Waiting for table to be ready..."
aws dynamodb wait table-exists --table-name $TABLE_NAME --region $REGION

echo "📊 Creating push token table..."
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
    2>/dev/null || echo "Push token table already exists"

echo "⏳ Waiting for push token table to be ready..."
aws dynamodb wait table-exists --table-name $PUSH_TOKEN_TABLE --region $REGION

# Step 2: Create IAM Role
echo "🔐 Creating IAM role..."
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://iam-policy.json \
    2>/dev/null || echo "Role already exists"

# Attach policies
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonSNSFullAccess

# Wait for role to propagate
echo "⏳ Waiting for IAM role to propagate..."
sleep 10

# Step 3: Create ECR repository for inference Lambda container
echo "🐳 Creating ECR repository for inference Lambda..."
ECR_REPO_NAME="health-inference-lambda"
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $REGION \
    2>/dev/null || echo "  ECR repository already exists"

# Get ECR repository URI
ECR_URI=$(aws ecr describe-repositories \
    --repository-names $ECR_REPO_NAME \
    --region $REGION \
    --query 'repositories[0].repositoryUri' \
    --output text)

echo "📦 ECR Repository: $ECR_URI"

# Login to ECR
echo "🔑 Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# Build inference Docker image
echo "🔨 Building inference Lambda container image..."
docker build -f Dockerfile.inference -t $ECR_REPO_NAME:latest .

# Tag and push to ECR
echo "⬆️  Pushing image to ECR..."
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
docker push $ECR_URI:latest

# Step 3.2: Package Lambda functions (code only - boto3 in runtime)
echo "📦 Packaging Lambda functions (code only)..."
rm -f function.zip notify.zip
zip function.zip lambda_function.py
zip notify.zip sns_to_expo.py

# Step 3.3: Create S3 bucket for model artifacts
echo "🪣 Creating S3 bucket for model artifacts..."
aws s3 mb s3://$MODEL_BUCKET --region $REGION 2>/dev/null || echo "  Bucket already exists or creation failed"

# Step 3.4: Upload model artifacts to S3
echo "🧠 Uploading model artifacts to S3..."
if [[ -f "$MODEL_LOCAL_PATH" && -f "$SCALER_LOCAL_PATH" ]]; then
    aws s3 cp "$MODEL_LOCAL_PATH" "s3://$MODEL_BUCKET/$MODEL_KEY" --region "$REGION" --no-verify-ssl || true
    aws s3 cp "$SCALER_LOCAL_PATH" "s3://$MODEL_BUCKET/$SCALER_KEY" --region "$REGION" --no-verify-ssl || true
else
    echo "⚠️  Model artifacts not found. Expected:"
    echo "   $MODEL_LOCAL_PATH"
    echo "   $SCALER_LOCAL_PATH"
    echo "   Skipping S3 upload."
fi

# Step 4: Create or Update Lambda function
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo "☁️  Deploying Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &>/dev/null; then
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://function.zip \
        --region $REGION
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
        --region $REGION
fi

echo "☁️  Deploying Anomaly Inference Lambda function (Container Image)..."
# Delete existing inference function if it's Zip type
if aws lambda get-function --function-name $INFERENCE_FUNCTION_NAME --region $REGION &>/dev/null; then
    CURRENT_TYPE=$(aws lambda get-function --function-name $INFERENCE_FUNCTION_NAME --region $REGION --query 'Configuration.PackageType' --output text)
    if [[ "$CURRENT_TYPE" == "Zip" ]]; then
        echo "  Deleting existing Zip-type function to recreate as Container Image..."
        aws lambda delete-function --function-name $INFERENCE_FUNCTION_NAME --region $REGION
        sleep 5
    fi
fi

# Create or update inference function with container image
if aws lambda get-function --function-name $INFERENCE_FUNCTION_NAME --region $REGION &>/dev/null; then
    aws lambda update-function-code \
        --function-name $INFERENCE_FUNCTION_NAME \
        --image-uri $ECR_URI:latest \
        --region $REGION
else
    aws lambda create-function \
        --function-name $INFERENCE_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ECR_URI:latest \
        --role $ROLE_ARN \
        --timeout 30 \
        --memory-size 1024 \
        --environment "{\"Variables\":{\"MODEL_BUCKET\":\"$MODEL_BUCKET\",\"MODEL_KEY\":\"$MODEL_KEY\",\"SCALER_KEY\":\"$SCALER_KEY\"}}" \
        --region $REGION
fi

echo "☁️  Deploying SNS to Expo Lambda function..."
if aws lambda get-function --function-name $NOTIFY_FUNCTION_NAME --region $REGION &>/dev/null; then
    aws lambda update-function-code \
        --function-name $NOTIFY_FUNCTION_NAME \
        --zip-file fileb://notify.zip \
        --region $REGION
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
        --region $REGION
fi

# Step 5: Create API Gateway
echo "🌐 Creating API Gateway..."
API_ID=$(aws apigateway create-rest-api \
    --name HealthMonitorAPI \
    --description "Health Monitoring System API" \
    --region $REGION \
    --query 'id' \
    --output text 2>/dev/null) || \
API_ID=$(aws apigateway get-rest-apis \
    --query "items[?name=='HealthMonitorAPI'].id" \
    --output text \
    --region $REGION)

echo "📝 API Gateway ID: $API_ID"

# Get root resource
ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query 'items[?path==`/`].id' \
    --output text \
    --region $REGION)

# Create resource
RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part health-data \
    --region $REGION \
    --query 'id' \
    --output text 2>/dev/null) || \
RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?path=='/health-data'].id" \
    --output text \
    --region $REGION)

# Create ingest resource
INGEST_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $RESOURCE_ID \
    --path-part ingest \
    --region $REGION \
    --query 'id' \
    --output text 2>/dev/null) || \
INGEST_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?path=='/health-data/ingest'].id" \
    --output text \
    --region $REGION)

# Create POST method
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $INGEST_ID \
    --http-method POST \
    --authorization-type NONE \
    --api-key-required \
    --region $REGION \
    2>/dev/null || echo "Method already exists"

# Set up Lambda integration
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $INGEST_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME/invocations \
    --region $REGION \
    2>/dev/null || echo "Integration already exists"

# Create sync resource
SYNC_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $RESOURCE_ID \
    --path-part sync \
    --region $REGION \
    --query 'id' \
    --output text 2>/dev/null) || \
SYNC_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?path=='/health-data/sync'].id" \
    --output text \
    --region $REGION)

# Create POST method for sync
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $SYNC_ID \
    --http-method POST \
    --authorization-type NONE \
    --api-key-required \
    --region $REGION \
    2>/dev/null || echo "Sync method already exists"

# Set up Lambda integration for sync
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $SYNC_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME/invocations \
    --region $REGION \
    2>/dev/null || echo "Sync integration already exists"

# Create notifications resource
NOTIFY_PARENT_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part notifications \
    --region $REGION \
    --query 'id' \
    --output text 2>/dev/null) || \
NOTIFY_PARENT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?path=='/notifications'].id" \
    --output text \
    --region $REGION)

REGISTER_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $NOTIFY_PARENT_ID \
    --path-part register \
    --region $REGION \
    --query 'id' \
    --output text 2>/dev/null) || \
REGISTER_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?path=='/notifications/register'].id" \
    --output text \
    --region $REGION)

aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $REGISTER_ID \
    --http-method POST \
    --authorization-type NONE \
    --api-key-required \
    --region $REGION \
    2>/dev/null || echo "Notification register method already exists"

aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $REGISTER_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME/invocations \
    --region $REGION \
    2>/dev/null || echo "Notification register integration already exists"

# Deploy API
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --region $REGION

# Create SNS topic
echo "📣 Creating SNS topic..."
SNS_TOPIC_ARN=$(aws sns create-topic \
    --name $SNS_TOPIC_NAME \
    --region $REGION \
    --query 'TopicArn' \
    --output text)

# Allow SNS to invoke notification Lambda
aws lambda add-permission \
    --function-name $NOTIFY_FUNCTION_NAME \
    --statement-id sns-invoke \
    --action lambda:InvokeFunction \
    --principal sns.amazonaws.com \
    --source-arn "$SNS_TOPIC_ARN" \
    --region $REGION \
    2>/dev/null || echo "SNS invoke permission already exists"

# Subscribe Lambda to SNS topic
aws sns subscribe \
    --topic-arn "$SNS_TOPIC_ARN" \
    --protocol lambda \
    --notification-endpoint "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$NOTIFY_FUNCTION_NAME" \
    --region "$REGION" \
    2>/dev/null || echo "SNS Lambda subscription already exists"

# Create SNS SMS subscription
if [[ -n "$SMS_SUBSCRIPTION_NUMBER" ]]; then
    echo "📲 Creating SNS SMS subscription for $SMS_SUBSCRIPTION_NUMBER..."
    aws sns subscribe \
        --topic-arn "$SNS_TOPIC_ARN" \
        --protocol sms \
        --notification-endpoint "$SMS_SUBSCRIPTION_NUMBER" \
        --region "$REGION" \
        2>/dev/null || echo "SMS subscription already exists or requires SMS sandbox approval"
fi

# Create API key and usage plan
echo "🔑 Creating API key and usage plan..."
API_KEY_ID=$(aws apigateway create-api-key \
    --name HealthMonitorApiKey \
    --enabled \
    --query 'id' \
    --output text 2>/dev/null) || \
API_KEY_ID=$(aws apigateway get-api-keys \
    --query "items[?name=='HealthMonitorApiKey'].id" \
    --output text \
    --region $REGION)

API_KEY_VALUE=$(aws apigateway get-api-key \
    --api-key $API_KEY_ID \
    --include-value \
    --query 'value' \
    --output text \
    --region $REGION)

USAGE_PLAN_ID=$(aws apigateway create-usage-plan \
    --name HealthMonitorUsagePlan \
    --api-stages apiId=$API_ID,stage=prod \
    --query 'id' \
    --output text 2>/dev/null) || \
USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
    --query "items[?name=='HealthMonitorUsagePlan'].id" \
    --output text \
    --region $REGION)

aws apigateway create-usage-plan-key \
    --usage-plan-id $USAGE_PLAN_ID \
    --key-id $API_KEY_ID \
    --key-type API_KEY \
    --region $REGION \
    2>/dev/null || echo "Usage plan key already exists"

# Update Lambda env with API key, SNS topic, and cloud inference function
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment "{\"Variables\":{\"TABLE_NAME\":\"$TABLE_NAME\",\"PUSH_TOKEN_TABLE\":\"$PUSH_TOKEN_TABLE\",\"REGION\":\"$REGION\",\"API_KEY\":\"$API_KEY_VALUE\",\"SNS_TOPIC_ARN\":\"$SNS_TOPIC_ARN\",\"CLOUD_INFERENCE_FUNCTION\":\"$INFERENCE_FUNCTION_NAME\"}}" \
    --region $REGION

# Add permission for API Gateway to invoke Lambda
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*" \
    --region $REGION \
    2>/dev/null || echo "Permission already exists"

# Step 6: Output API endpoint
API_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/health-data/ingest"
SYNC_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/health-data/sync"
REGISTER_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/notifications/register"

echo ""
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 API Endpoint: $API_ENDPOINT"
echo "📍 Sync Endpoint: $SYNC_ENDPOINT"
echo "📍 Register Push Token: $REGISTER_ENDPOINT"
echo "🔑 DynamoDB Table: $TABLE_NAME"
echo "🔑 Push Token Table: $PUSH_TOKEN_TABLE"
echo "⚡ Lambda Function: $FUNCTION_NAME"
echo "🧠 Inference Lambda: $INFERENCE_FUNCTION_NAME"
echo "📲 Notify Lambda: $NOTIFY_FUNCTION_NAME"
echo "📣 SNS Topic: $SNS_TOPIC_ARN"
echo "🔐 API Key: $API_KEY_VALUE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔧 Next Steps:"
echo "1. Update WearOSApp ApiConfig.kt with:"
echo "   const val BASE_URL = \"https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/\""
echo ""
echo "2. Test the endpoint:"
echo "   curl -X POST $API_ENDPOINT \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -H 'X-API-Key: $API_KEY_VALUE' \\"
echo "     -d @test-payload.json"
echo ""

# Cleanup
rm -rf package function.zip notify.zip "$LAYER_DIR" "$LAYER_ZIP"
