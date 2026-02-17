# AI Governance Copilot (Local-First)

AI Governance Copilot is a local-first governance control plane for dbt projects. It enforces policy-as-code gates to prevent sensitive data (PII) from leaking into self-service datasets while enabling an explicit, auditable workflow for a restricted tier.

## What problem this solves

Data governance is often manual and inconsistent:
- PII accidentally lands in broadly accessible analytics tables.
- Ownership and accountability metadata is missing.
- Exceptions happen informally with no durable evidence trail.

This project shifts governance left into dbt delivery workflows:
- `gold` (self-service): PII blocked.
- `gold_restricted`: PII allowed only with explicit approved exception.
- Every run produces machine-readable evidence.

## Architecture at a glance

Flow:
`dbt build -> scanner findings -> OPA reasons -> evidence log -> pass/fail gate`

Main components:
- `dbt/gov_copilot_dbt`: data models and synthetic seeds.
- `scanner/`: scanner and evidence writer.
- `policies/`: Rego policies (OPA).
- `standards/`: classification and exception inputs.
- `artifacts/`: generated findings/reasons.
- `evidence/`: append-only run events.

More details: `docs/ARCHITECTURE.md`

## Repository structure

- `dbt/gov_copilot_dbt/` dbt project (silver, gold, gold_restricted)
- `scanner/run_scan.py` scanner
- `scanner/write_evidence.py` evidence writer
- `policies/governance.rego` OPA policy file
- `standards/` policy inputs (`data_classification.json`, `exceptions.yml`)
- `artifacts/` generated run outputs
- `evidence/` append-only `evidence.jsonl`
- `.github/workflows/governance.yml` CI workflow
- `run_local.sh` one-command local governance run

## Prerequisites

- Docker Desktop
- Python 3.11+
- dbt (`dbt-postgres`) in a virtual environment
- OPA CLI (`opa version` should work)

## Security note

This repository uses local/demo credentials via environment variables. Do not reuse these values in real environments.

- Local Docker credentials come from `.env` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`).
- CI reads DB password from GitHub Actions secret `POSTGRES_PASSWORD`.
- Postgres is bound to `127.0.0.1` by default to reduce exposure.

## Quick start

From repo root:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install dbt-postgres
docker compose up -d
```

Create/update your dbt profile at `~/.dbt/profiles.yml`:

```yaml
gov_copilot_dbt:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: postgres
      password: postgres
      port: 5432
      dbname: governance
      schema: public
      threads: 1
```

Run the full local pipeline:

```bash
./run_local.sh
```

## What `run_local.sh` does

1. `dbt seed`
2. `dbt run`
3. `dbt test`
4. scanner writes `artifacts/findings.json`
5. OPA evaluates policy and writes `artifacts/reasons.json`
6. evidence writer appends `evidence/evidence.jsonl`
7. gate exits non-zero on deny

## Outputs

- `artifacts/findings.json`
- `artifacts/reasons.json`
- `evidence/evidence.jsonl`

## Current policy behavior (MVP)

- Block PII-like columns in `gold` models.
- Require exception for PII-like columns in `gold_restricted`.
- Enforce exception expiry in policy.

## CI

GitHub Actions workflow: `.github/workflows/governance.yml`
- Runs on PR
- Sets up Python, dbt, and OPA
- Starts Postgres via Docker Compose
- Runs the same local governance pipeline
- Uploads governance artifacts
- Requires repo secret: `POSTGRES_PASSWORD`

## Additional docs

- `docs/LOCAL_SETUP.md`
- `docs/ARCHITECTURE.md`
