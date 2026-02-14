# Architecture — AI Governance Copilot (Local-First)

## Purpose
AI Governance Copilot is a local-first governance control plane for dbt projects. It enforces policy-as-code gates that:
- prevent PII from leaking into self-service Gold datasets
- enable an explicit, auditable workflow for a Restricted Gold tier
- create evidence trails that answer “who did what and why”

The design intentionally separates:
- **Data plane** (dbt + warehouse)
- **Control plane** (scanner + policy + evidence)
- **UX** (copilot feedback in PR/CI)

---

## Problem Statement
Data governance often fails because it’s:
- manual and inconsistent
- enforced late (after release)
- disconnected from engineering workflow
- not auditable (approvals happen informally)

This project shifts governance left into PR/CI and produces deterministic decisions with a durable audit trail.

---

## Core Concepts

### Tiers (Consumption Layers)
We publish two consumption tiers as separate products:

#### Gold (Self-Service)
- Intended for broad analytics and dashboards
- Must be **PII-minimized**
- Feeds semantic/metric definitions
- Governance: **PII is blocked**

#### Gold Restricted
- Intended for identity-enabled operational analytics
- May contain PII only with explicit approval
- Separate namespace (schema/folder naming)
- Governance: **PII allowed only with approval + evidence + declared controls**

> Practical rule: Gold is “safe by default.” Restricted is “need-to-know with evidence.”

### Policy-as-Code
Policies are deterministic rules (OPA/Rego) that evaluate machine-readable findings and metadata. LLMs (optional) may assist with explanation, but they do not decide.

### Evidence-First Governance
Every run produces evidence:
- what changed
- what was detected (findings)
- which policies fired (reasons)
- what decision was made (allow/deny)
- which exceptions were used and who approved them

---

## High-Level Workflow

### PR / Local run flow (shift-left gate)
1. **dbt generates artifacts** (`manifest.json`, `run_results.json`)
2. **Scanner** reads dbt artifacts (and optionally git diff) and emits:
   - `artifacts/findings.json`
3. **Policy Engine (OPA)** evaluates findings + exceptions:
   - outputs allow/deny + reasons
4. **Copilot output** (later in CI):
   - PR comment or console summary with remediation actions
5. **Evidence** is written as an append-only record

### Main branch / release flow
- Runs the same governance gate
- Runs dbt build
- Writes a “release evidence” record

---

## Architecture Diagram (Text)

Developer → GitHub PR/Local Run
- Changes dbt models and metadata

Data Plane (Warehouse + dbt)
- Postgres (local Docker) / Snowflake (cloud)
- dbt builds Silver/Gold/Restricted models
- dbt produces artifacts for governance

Control Plane (Governance Copilot)
- Scanner → produces findings JSON
- OPA/Rego → evaluates policies; allow/deny + reasons
- Evidence logger → append-only audit output

UX Plane
- Console output (MVP)
- GitHub PR comment (later)
- Minimal policy catalog / evidence viewer (optional later)

---

## Components and Responsibilities

### 1) dbt Project (`dbt/`)
Responsibilities:
- Define layer conventions (silver/gold/gold_restricted)
- Publish business-ready datasets
- Provide metadata needed for governance (owner/domain/layer/sensitivity)

Key outputs:
- `target/manifest.json` (model graph, columns, meta)
- `target/run_results.json` (what ran and status)

### 2) Scanner (`scanner/`)
Responsibilities:
- Read dbt artifacts and identify risk
- Emit machine-readable findings

Example findings:
- `pii_detected`: likely PII columns detected
- `missing_meta`: required model meta missing
- (later) `missing_tests`, `unapproved_restricted_asset`, etc.

Output contract (MVP):
- `artifacts/findings.json`:
  - `project`
  - `manifest_path`
  - `findings[]`:
    - `type`, `model`, `layer`, `severity`, `details`

### 3) Policy Engine (OPA/Rego) (`policies/`)
Responsibilities:
- Evaluate findings deterministically
- Produce allow/deny + reasons + required actions

Policy examples:
- Deny PII in Gold (self-service)
- Allow PII in Restricted only if there is a valid approval/exception
- Deny missing `meta.owner`/`meta.domain` on Gold/Restricted models

Output (MVP):
- allow boolean
- reasons list (human-readable strings)

### 4) Standards & Exceptions (`standards/`)
Responsibilities:
- Store governance standards and approvals in-repo for MVP
- Simulate real workflows (ticketing/approvals) via YAML

Files:
- `standards/exceptions.yml`:
  - approved exceptions with reason + approver + expiry

### 5) Evidence (`evidence/`)
Responsibilities:
- Append-only audit artifacts per run
- Provide a durable record of decisions

MVP storage:
- JSON or JSONL files written locally (and uploaded as CI artifacts later)

---

## Tiering Rules (Authoritative)

### Gold (Self-Service)
- **Blocked:** direct PII columns (email, phone, name, ssn, dob, etc.)
- **Allowed:** surrogate IDs (customer_id, account_id), coarse attributes (region)
- **Required metadata:** owner, domain, layer, sensitivity
- **Required tests (recommended):** primary key not_null + unique for facts/dims

### Gold Restricted
- **Allowed:** PII only if:
  - model is explicitly in restricted tier (folder/schema naming)
  - `meta.sensitivity = restricted`
  - an approval entry exists in `standards/exceptions.yml`
  - approval is not expired
  - controls are declared (masking/RLS strategy; simulated locally)

---

## Snowflake Integration Strategy (Design)
The governance control plane remains unchanged.

Only change:
- dbt target (Postgres → Snowflake)
- enforcement becomes real via Snowflake features:
  - classification tags
  - dynamic data masking policies
  - row access policies
  - separate schemas/roles

Recommended split:
- PR checks run on Postgres (fast)
- Main branch builds run on Snowflake (production-like)

---

## Non-Goals (MVP)
- Full enterprise RBAC provisioning system
- Full data catalog UI
- Multi-agent orchestration
- LLM-based approval decisions
