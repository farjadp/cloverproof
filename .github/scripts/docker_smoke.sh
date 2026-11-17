#!/usr/bin/env bash
# Smoke test for the app image (Dockerfile), used by CI and runnable locally:
#   docker build -t cloverproof-app:ci . && .github/scripts/docker_smoke.sh cloverproof-app:ci
# Starts a throwaway PostGIS on a private docker network, migrates it from the image (as the
# operator would), creates a least-privilege login, then checks that the image
#   1. refuses a superuser DATABASE_URL in staging (ADR 0007), and
#   2. starts as cp_app_login in staging, reports healthy, and serves GET /healthz.
# All passwords below are throwaway values for a container destroyed at the end.
set -euo pipefail

IMAGE="${1:?usage: docker_smoke.sh IMAGE}"
PG_IMAGE="${PG_IMAGE:-postgis/postgis:18-3.7}"
RUN_ID="cpsmoke-$$"
NET="$RUN_ID-net"
DB="$RUN_ID-db"
APP="$RUN_ID-app"
HOST_NAME="app.smoke.test"
SUPER_URL="postgresql://postgres:smoke-throwaway@$DB:5432/postgres"
APP_URL="postgresql://cp_app_login:smoke-throwaway-app@$DB:5432/postgres"
SECRET="smoke-only-session-secret-0123456789abcdef"

cleanup() {
  docker logs "$APP" >/dev/null 2>&1 && { echo "--- app logs ---"; docker logs "$APP" 2>&1 | tail -30; }
  docker rm -f "$APP" "$DB" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$NET" >/dev/null
docker run -d --name "$DB" --network "$NET" -e POSTGRES_PASSWORD=smoke-throwaway \
  --health-cmd "pg_isready -h 127.0.0.1 -U postgres" --health-interval 2s --health-retries 60 \
  "$PG_IMAGE" >/dev/null

echo "waiting for PostGIS"
for _ in $(seq 1 90); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' "$DB")" = healthy ] && break
  sleep 2
done
[ "$(docker inspect -f '{{.State.Health.Status}}' "$DB")" = healthy ]

echo "migrating (operator step, not part of container start)"
docker run --rm --network "$NET" -e DATABASE_URL="$SUPER_URL" "$IMAGE" \
  python -m cloverproof_app.db.migrate up | tail -3
docker exec "$DB" psql -q -U postgres -v ON_ERROR_STOP=1 \
  -c "create role cp_app_login login password 'smoke-throwaway-app' in role cp_app;"

common=(--network "$NET" -e ENV=staging -e SESSION_SECRET="$SECRET" -e ALLOWED_HOSTS="$HOST_NAME")

echo "check 1: superuser DATABASE_URL must be refused"
if docker run --rm "${common[@]}" -e DATABASE_URL="$SUPER_URL" "$IMAGE" \
  >"${RUNNER_TEMP:-/tmp}/$RUN_ID-super.log" 2>&1; then
  echo "FAIL: app ran with a superuser login"; exit 1
fi
grep -q "superuser" "${RUNNER_TEMP:-/tmp}/$RUN_ID-super.log" \
  || { echo "FAIL: exited, but not with the superuser refusal"; tail -20 "${RUNNER_TEMP:-/tmp}/$RUN_ID-super.log"; exit 1; }
echo "ok: superuser refused"

echo "check 2: cp_app_login starts and is healthy"
docker run -d --name "$APP" "${common[@]}" -e DATABASE_URL="$APP_URL" -e PORT=8080 \
  --health-interval 2s --health-start-period 5s "$IMAGE" >/dev/null
status=starting
for _ in $(seq 1 45); do
  status="$(docker inspect -f '{{.State.Health.Status}}' "$APP" 2>/dev/null || echo gone)"
  [ "$status" = healthy ] || [ "$status" = unhealthy ] || [ "$status" = gone ] && break
  sleep 2
done
[ "$status" = healthy ] || { echo "FAIL: container health is $status"; exit 1; }
body="$(docker exec "$APP" python -c "import http.client as h; c=h.HTTPConnection('127.0.0.1', 8080, timeout=3); c.request('GET', '/healthz', headers={'Host': '$HOST_NAME'}); r=c.getresponse(); print(r.status, r.read().decode())")"
echo "GET /healthz -> $body"
[ "$body" = '200 {"status":"ok"}' ] || { echo "FAIL: unexpected /healthz response"; exit 1; }
echo "smoke OK"
