#!/bin/bash

# AWS Lambda Deployment Script for Health Monitoring System

set -e

echo "🚀 Deploying Health Monitoring Cloud Backend..."

# Configuration
FUNCTION_NAME="HealthDataIngestion"
RUNTIME="python3.9"
HANDLER="lambda_function.lambda_handler"
ROLE_NAME="HealthMonitorLambdaRole"
TABLE_NAME="HealthMetrics"
REGION="us-east-1"

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

# Wait for role to propagate
echo "⏳ Waiting for IAM role to propagate..."
sleep 10

# Step 3: Package Lambda function
echo "📦 Packaging Lambda function..."
rm -f function.zip
pip install -r requirements.txt -t ./package
cd package && zip -r ../function.zip . && cd ..
zip -g function.zip lambda_function.py

# Step 4: Create or Update Lambda function
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo "☁️  Deploying Lambda function..."
aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --runtime $RUNTIME \
    --role $ROLE_ARN \
    --handler $HANDLER \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 512 \
    --environment Variables={TABLE_NAME=$TABLE_NAME,REGION=$REGION} \
    --region $REGION \
    2>/dev/null || \
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://function.zip \
    --region $REGION

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

# Deploy API
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
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

echo ""
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 API Endpoint: $API_ENDPOINT"
echo "🔑 DynamoDB Table: $TABLE_NAME"
echo "⚡ Lambda Function: $FUNCTION_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔧 Next Steps:"
echo "1. Update WearOSApp ApiConfig.kt with:"
echo "   const val BASE_URL = \"https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/\""
echo ""
echo "2. Test the endpoint:"
echo "   curl -X POST $API_ENDPOINT \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -H 'X-API-Key: your-api-key' \\"
echo "     -d @test-payload.json"
echo ""

# Cleanup
rm -rf package function.zip
