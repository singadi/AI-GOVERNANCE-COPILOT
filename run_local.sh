#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x "$ROOT_DIR/.venv/bin/dbt" ]]; then
  DBT_BIN="$ROOT_DIR/.venv/bin/dbt"
else
  DBT_BIN="dbt"
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

mkdir -p artifacts evidence
rm -f artifacts/findings.json artifacts/reasons.json evidence/evidence.jsonl

echo "== dbt build =="
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

# Store reasons in JSON artifact for evidence logger
opa eval -f json -d "$ROOT_DIR/policies" -i "$ROOT_DIR/artifacts/findings.json" "data.gov.reasons" > "$ROOT_DIR/artifacts/reasons.json"

echo "== evidence =="
"$PYTHON_BIN" "$ROOT_DIR/scanner/write_evidence.py"

if [ "$ALLOW" != "true" ]; then
  echo "Governance gate failed"
  exit 1
fi

echo "Governance gate passed"
