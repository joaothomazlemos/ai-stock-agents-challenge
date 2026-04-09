#!/usr/bin/env bash
set -euo pipefail

BUCKET="${1:?Usage: bash bootstrap.sh <globally-unique-bucket-name>}"
REGION="${2:-us-east-1}"

echo "Creating S3 bucket for Terraform state: ${BUCKET} (region: ${REGION})"

if aws s3api head-bucket --bucket "${BUCKET}" 2>/dev/null; then
  echo "Bucket already exists, skipping creation."
else
  aws s3api create-bucket \
    --bucket "${BUCKET}" \
    --region "${REGION}"

  aws s3api put-bucket-versioning \
    --bucket "${BUCKET}" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption \
    --bucket "${BUCKET}" \
    --server-side-encryption-configuration '{
      "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }'

  aws s3api put-public-access-block \
    --bucket "${BUCKET}" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

  echo "Bucket created with versioning, encryption, and public access block."
fi

echo "Now update terraform/providers.tf backend \"s3\" block with bucket = \"${BUCKET}\""
echo "Then run 'terraform init' to initialize the backend."
