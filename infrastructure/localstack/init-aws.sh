#!/bin/bash
# LocalStack initialization script
# This script runs when LocalStack is ready

set -e

echo "Initializing LocalStack resources for SDLC Agent Squad..."

# Create DynamoDB table for conversation storage
echo "Creating DynamoDB table: sdlc-agent-conversations"
awslocal dynamodb create-table \
    --table-name sdlc-agent-conversations \
    --attribute-definitions \
        AttributeName=pk,AttributeType=S \
        AttributeName=sk,AttributeType=S \
    --key-schema \
        AttributeName=pk,KeyType=HASH \
        AttributeName=sk,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --tags Key=Environment,Value=local Key=Application,Value=sdlc-agent-squad

# Create S3 bucket for artifacts
echo "Creating S3 bucket: sdlc-agent-artifacts"
awslocal s3 mb s3://sdlc-agent-artifacts
awslocal s3api put-bucket-tagging \
    --bucket sdlc-agent-artifacts \
    --tagging 'TagSet=[{Key=Environment,Value=local},{Key=Application,Value=sdlc-agent-squad}]'

# Create SQS queue for async processing
echo "Creating SQS queue: sdlc-agent-events"
awslocal sqs create-queue \
    --queue-name sdlc-agent-events \
    --tags Environment=local,Application=sdlc-agent-squad

# Create API Gateway for webhooks (optional)
echo "Creating API Gateway: sdlc-webhook-api"
API_ID=$(awslocal apigateway create-rest-api \
    --name "sdlc-webhook-api" \
    --description "SDLC Agent Squad Webhook API" \
    --query 'id' \
    --output text)

echo "API Gateway created with ID: $API_ID"

# Get root resource
ROOT_RESOURCE=$(awslocal apigateway get-resources \
    --rest-api-id "$API_ID" \
    --query 'items[0].id' \
    --output text)

# Create /webhook resource
WEBHOOK_RESOURCE=$(awslocal apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$ROOT_RESOURCE" \
    --path-part "webhook" \
    --query 'id' \
    --output text)

echo "Webhook resource created: $WEBHOOK_RESOURCE"

echo ""
echo "=========================================="
echo "LocalStack initialization complete!"
echo "=========================================="
echo ""
echo "Resources created:"
echo "  - DynamoDB Table: sdlc-agent-conversations"
echo "  - S3 Bucket: sdlc-agent-artifacts"
echo "  - SQS Queue: sdlc-agent-events"
echo "  - API Gateway: sdlc-webhook-api (ID: $API_ID)"
echo ""
echo "LocalStack endpoint: http://localhost:4566"
echo ""
