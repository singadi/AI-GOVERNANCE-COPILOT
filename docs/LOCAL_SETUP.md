# Local Setup

## Prereqs
- Docker Desktop
- dbt with `dbt-postgres`
- OPA CLI

## Start Postgres
```bash
docker compose up -d
```

## Run Full Governance Flow
From repo root:
```bash
./run_local.sh
```

## Outputs
- `artifacts/findings.json`
- `artifacts/reasons.json`
- `evidence/evidence.jsonl`
