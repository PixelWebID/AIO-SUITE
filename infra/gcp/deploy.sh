#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PROJECT_ID:-}" ]]; then
  echo "PROJECT_ID environment variable is required" >&2
  exit 1
fi

REGION=${REGION:-us-central1}
TAG=${TAG:-$(git rev-parse --short HEAD)}
REGISTRY="gcr.io/${PROJECT_ID}"

CONTENT_IMAGE="${REGISTRY}/aio-content-intel:${TAG}"
SOCIAL_IMAGE="${REGISTRY}/aio-social-hub:${TAG}"

echo "Building containers..."
docker build -t "${CONTENT_IMAGE}" ./apps/content-intel
docker build -t "${SOCIAL_IMAGE}" ./apps/social-hub

echo "Authenticating with Google Container Registry..."
gcloud auth configure-docker --quiet

echo "Pushing images..."
docker push "${CONTENT_IMAGE}"
docker push "${SOCIAL_IMAGE}"

CONTENT_SERVICE=${CONTENT_SERVICE:-aio-content-intel}
SOCIAL_SERVICE=${SOCIAL_SERVICE:-aio-social-hub}

CONTENT_ENV=${CONTENT_ENV:-PYTHONUNBUFFERED=1}
SOCIAL_ENV=${SOCIAL_ENV:-SOCIAL_DEFAULT_TONE=casual}
CONTENT_SECRETS=${CONTENT_SECRETS:-OPENAI_API_KEY=projects/${PROJECT_ID}/secrets/openai_key:latest}
SOCIAL_SECRETS=${SOCIAL_SECRETS:-OPENAI_API_KEY=projects/${PROJECT_ID}/secrets/openai_key:latest}

echo "Deploying Content Intelligence service..."
gcloud run deploy "${CONTENT_SERVICE}" \
  --image "${CONTENT_IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "${CONTENT_ENV}" \\\n  --set-secrets "${CONTENT_SECRETS}"

echo "Deploying Social Hub service..."
gcloud run deploy "${SOCIAL_SERVICE}" \
  --image "${SOCIAL_IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "${SOCIAL_ENV}" \\\n  --set-secrets "${SOCIAL_SECRETS}"

CONTENT_URL=$(gcloud run services describe "${CONTENT_SERVICE}" --region "${REGION}" --format='value(status.url)')
SOCIAL_URL=$(gcloud run services describe "${SOCIAL_SERVICE}" --region "${REGION}" --format='value(status.url)')

echo "\nDeployment complete"
echo "Content Intelligence URL: ${CONTENT_URL}"
echo "Social Hub URL: ${SOCIAL_URL}"

