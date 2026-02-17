#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-governance}"

if command -v dbt >/dev/null 2>&1; then
  DBT_BIN="dbt"
elif [[ -x "$ROOT_DIR/.venv/bin/dbt" ]]; then
  DBT_BIN="$ROOT_DIR/.venv/bin/dbt"
else
  echo "dbt not found"
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  echo "python not found"
  exit 1
fi

mkdir -p "$ROOT_DIR/artifacts" "$ROOT_DIR/evidence"
rm -f "$ROOT_DIR/artifacts/findings.json" "$ROOT_DIR/artifacts/reasons.json" "$ROOT_DIR/evidence/evidence.jsonl"

echo "== wait for postgres =="
for i in {1..30}; do
  if docker exec -i govcopilot-postgres pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
    echo "Postgres is ready"
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "Postgres did not become ready in time"
    exit 1
  fi
  echo "Waiting for Postgres... ($i/30)"
  sleep 2
done

echo "== dbt seed/run/test =="
(
  cd "$ROOT_DIR/dbt/gov_copilot_dbt"
  "$DBT_BIN" seed --full-refresh
  "$DBT_BIN" run
  "$DBT_BIN" test
)

echo "== scan =="
"$PYTHON_BIN" "$ROOT_DIR/scanner/run_scan.py"

echo "== policy eval =="
ALLOW=$(opa eval -f raw -d "$ROOT_DIR/policies" -i "$ROOT_DIR/artifacts/findings.json" "data.gov.allow")
echo "allow=$ALLOW"

opa eval -f json -d "$ROOT_DIR/policies" -i "$ROOT_DIR/artifacts/findings.json" "data.gov.reasons" > "$ROOT_DIR/artifacts/reasons.json"

echo "== evidence =="
"$PYTHON_BIN" "$ROOT_DIR/scanner/write_evidence.py"

if [ "$ALLOW" != "true" ]; then
  echo "Governance gate failed"
  opa eval -f pretty -d "$ROOT_DIR/policies" -i "$ROOT_DIR/artifacts/findings.json" "data.gov.reasons"
  exit 1
fi

echo "Governance gate passed"
