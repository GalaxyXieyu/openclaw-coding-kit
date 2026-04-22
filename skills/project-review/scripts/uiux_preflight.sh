#!/usr/bin/env bash
set -euo pipefail

WEB_URL="${WEB_URL:-http://localhost:30010/login}"
ADMIN_URL="${ADMIN_URL:-http://localhost:30020/login}"
API_HEALTH_URL="${API_HEALTH_URL:-http://localhost:30011/health}"
LINT_CMD="${LINT_CMD:-pnpm -r lint}"
BUILD_CMD="${BUILD_CMD:-pnpm -r build}"
SKIP_LINT=0
SKIP_BUILD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --)
      shift
      ;;
    --web-url)
      WEB_URL="$2"
      shift 2
      ;;
    --admin-url)
      ADMIN_URL="$2"
      shift 2
      ;;
    --api-health-url)
      API_HEALTH_URL="$2"
      shift 2
      ;;
    --lint-cmd)
      LINT_CMD="$2"
      shift 2
      ;;
    --build-cmd)
      BUILD_CMD="$2"
      shift 2
      ;;
    --skip-lint)
      SKIP_LINT=1
      shift
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    *)
      echo "[preflight] unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

echo "[preflight] start"
echo "[preflight] WEB_URL=${WEB_URL}"
echo "[preflight] ADMIN_URL=${ADMIN_URL}"
echo "[preflight] API_HEALTH_URL=${API_HEALTH_URL}"

if [[ "${SKIP_LINT}" -eq 0 ]]; then
  echo "[preflight] lint"
  eval "${LINT_CMD}"
fi

if [[ "${SKIP_BUILD}" -eq 0 ]]; then
  echo "[preflight] build"
  eval "${BUILD_CMD}"
fi

echo "[preflight] check api health"
curl -fsS "${API_HEALTH_URL}" >/dev/null

echo "[preflight] check web entry"
curl -fsSI "${WEB_URL}" >/dev/null

echo "[preflight] check admin entry"
curl -fsSI "${ADMIN_URL}" >/dev/null

echo "[preflight] PASS"
