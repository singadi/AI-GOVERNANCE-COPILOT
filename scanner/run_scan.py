# scanner/run_scan.py
"""
AI Governance Copilot - Scanner (Fast MVP)

What this scanner does:
- Reads dbt target/manifest.json
- For each dbt model:
  - verifies required meta fields exist (owner, domain, layer, sensitivity)
  - detects likely PII by:
      1) manifest columns (if provided via schema.yml), else
      2) fallback to scanning SQL text (raw_code/compiled_code) for PII tokens
- Writes artifacts/findings.json for OPA (policy engine) to evaluate

Assumptions (match our repo layout):
- dbt project lives at: dbt/gov_copilot_dbt
- dbt artifacts live at: dbt/gov_copilot_dbt/target/manifest.json
- exceptions approvals live at: standards/exceptions.yml
- outputs to: artifacts/findings.json
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = REPO_ROOT / "dbt" / "gov_copilot_dbt"
MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
EXCEPTIONS_PATH = REPO_ROOT / "standards" / "exceptions.yml"

# Simple heuristics for MVP
PII_TOKENS = ["email", "phone", "ssn", "dob", "first_name", "last_name", "full_name"]

# Column-name patterns (if manifest has column metadata)
PII_COL_PATTERNS = [
    re.compile(r".*email.*", re.IGNORECASE),
    re.compile(r".*phone.*", re.IGNORECASE),
    re.compile(r".*ssn.*", re.IGNORECASE),
    re.compile(r".*dob.*", re.IGNORECASE),
    re.compile(r".*first_name.*", re.IGNORECASE),
    re.compile(r".*last_name.*", re.IGNORECASE),
    re.compile(r".*full_name.*", re.IGNORECASE),
]


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r") as f:
        return yaml.safe_load(f) or {}


def load_manifest(path: Path) -> Dict[str, Any]:
    with path.open("r") as f:
        return json.load(f)


def detect_pii_from_columns(columns: Dict[str, Any]) -> List[str]:
    """Detect PII by column names listed in manifest columns dict."""
    hits: List[str] = []
    for col_name in columns.keys():
        if any(p.match(col_name) for p in PII_COL_PATTERNS):
            hits.append(col_name)
    return sorted(set(hits))


def detect_pii_from_sql(sql_text: str) -> List[str]:
    """Detect PII tokens from SQL text (very simple MVP heuristic)."""
    hits: List[str] = []
    if not sql_text:
        return hits
    # Remove SQL comments so commented-out tokens do not trigger findings.
    no_block_comments = re.sub(r"/\*.*?\*/", " ", sql_text, flags=re.DOTALL)
    no_comments = re.sub(r"--.*?$", " ", no_block_comments, flags=re.MULTILINE)
    for token in PII_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", no_comments, re.IGNORECASE):
            hits.append(token)
    return sorted(set(hits))


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            f"manifest.json not found at {MANIFEST_PATH}\n"
            f"Run from dbt project dir: `dbt run` (or `dbt compile`) first."
        )

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(MANIFEST_PATH)
    exceptions_doc = load_yaml(EXCEPTIONS_PATH)
    exceptions = exceptions_doc.get("exceptions", []) or []

    findings: List[Dict[str, Any]] = []
    nodes: Dict[str, Any] = manifest.get("nodes", {}) or {}

    for _, node in nodes.items():
        if node.get("resource_type") != "model":
            continue

        model_name = node.get("name")
        meta = node.get("meta") or {}
        layer = (meta.get("layer") or "unknown").lower()
        sensitivity = (meta.get("sensitivity") or "unknown").lower()

        # 1) Required metadata check
        required_meta = ["owner", "domain", "layer", "sensitivity"]
        missing = [k for k in required_meta if not meta.get(k)]
        if missing:
            findings.append(
                {
                    "type": "missing_meta",
                    "model": model_name,
                    "layer": layer,
                    "severity": "high" if layer in ("gold", "gold_restricted") else "medium",
                    "details": {"missing": missing},
                }
            )

        # 2) PII detection
        # Prefer explicit column definitions (from schema.yml) if present,
        # otherwise scan SQL text (raw_code/compiled_code) as fallback.
        columns = node.get("columns") or {}
        pii_hits = detect_pii_from_columns(columns)
        source = "manifest_columns"

        if not pii_hits:
            sql_text = node.get("compiled_code") or node.get("raw_code") or ""
            pii_hits = detect_pii_from_sql(sql_text)
            source = "sql_fallback"

        if pii_hits:
            findings.append(
                {
                    "type": "pii_detected",
                    "model": model_name,
                    "layer": layer,
                    "severity": "high" if layer == "gold" else "medium",
                    "details": {"columns": pii_hits, "source": source, "sensitivity": sensitivity},
                }
            )

    out = {
        "project": "gov_copilot_dbt",
        "manifest_path": str(MANIFEST_PATH),
        "exceptions": exceptions,
        "findings": findings,
    }

    out_path = ARTIFACTS_DIR / "findings.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote findings to {out_path}")
    print(f"Findings: {len(findings)}")


if __name__ == "__main__":
    main()
