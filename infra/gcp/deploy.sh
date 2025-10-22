#!/usr/bin/env bash

set -euo pipefail

SERVICE_NAME="${1:-content-intel}"
PROJECT_ID="${GCP_PROJECT:?GCP_PROJECT env var must be set}"
REGION="${GCP_REGION:-asia-southeast2}"
IMAGE="${GCP_IMAGE:-gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest}"

echo "Deploying ${SERVICE_NAME} to Cloud Run (project=${PROJECT_ID}, region=${REGION})"

gcloud config set project "${PROJECT_ID}"
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated

echo "Deployment completed."
