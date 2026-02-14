
---

## AGENTS.md (Agent instructions for contributions)

```markdown
# AGENTS.md — How to work in this repo

This file describes how humans and AI agents should work in this repository.

## Purpose
This repo implements a local-first Governance Copilot for dbt projects:
- Detect governance risk (PII, missing metadata, missing tests)
- Enforce policy-as-code gates (OPA/Rego)
- Generate copilot-style remediation output
- Produce an audit/evidence trail

## Golden Rules
1) **Deterministic decisions**: policies decide allow/deny. LLMs (if used) may explain, not decide.
2) **PII never in self-service Gold**: default tier must remain PII-minimized.
3) **Restricted tier requires evidence**: PII in restricted outputs must be accompanied by approval metadata + expiry.
4) **Everything is auditable**: scanning input, decisions, and exceptions are logged.

## Repo Contracts (Inputs/Outputs)

### Scanner
**Input**
- dbt `target/manifest.json`
- optional: `git diff` for changed models
- `standards/` config (classification rules, exceptions)

**Output**
- `artifacts/findings.json` with structure:
  - project info
  - list of findings:
    - `type`, `model`, `layer`, `severity`, `details`

### Policy Engine (OPA/Rego)
**Input**
- `artifacts/findings.json`
- `standards/exceptions.yml`

**Output**
- allow/deny decision
- reasons list
- optional: remediation steps

### Evidence
**Input**
- commit/pr metadata (when available)
- findings + decision + exceptions used

**Output**
- append-only record in `evidence/` (JSONL preferred)

## Definition of Tiers

### Gold (self-service)
- Broad analytics consumption
- Must be PII-minimized
- Policies: PII blocked; owner/domain required

### Gold Restricted
- Need-to-know, identity-enabled use cases
- PII may be present only if:
  - approved exception exists
  - expiry is set
  - additional controls are declared (masking/RLS strategy)
  - evidence record is written

## Coding Guidelines
- Keep fast MVP scripts small and readable.
- Prefer simple JSON/YAML contracts.
- Avoid introducing paid dependencies; local-first.
- Keep secrets out of the repo. Use `.env` for local overrides.
- Add/maintain `README.md` whenever workflows change.

## How to Add a New Policy
1) Add a Rego rule in `policies/`.
2) Add/extend tests via fixture findings JSON files (recommended).
3) Update README “Policies” section to describe behavior.
4) Ensure policy produces actionable reasons (human-readable).

## How to Add a New Finding Type
1) Extend scanner to emit a new finding `type`.
2) Add example output to `docs/` or fixtures.
3) Add a corresponding policy rule (if gating is required).
4) Ensure evidence includes this new finding type.

## Suggested Demo Script
- Show a PR that introduces PII into Gold → gate fails.
- Move it to Gold Restricted + add exception entry → gate passes.
- Show evidence record containing approver and expiry.

## Non-Goals (for MVP)
- Not a full data catalog
- Not a full RBAC provisioning system
- Not multi-agent orchestration
- Not an LLM-first chatbot
