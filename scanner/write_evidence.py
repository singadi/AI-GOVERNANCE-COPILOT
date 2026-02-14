# scanner/write_evidence.py
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FINDINGS_PATH = REPO_ROOT / "artifacts" / "findings.json"
REASONS_PATH = REPO_ROOT / "artifacts" / "reasons.json"
EVIDENCE_DIR = REPO_ROOT / "evidence"
EVIDENCE_FILE = EVIDENCE_DIR / "evidence.jsonl"


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def safe_git(cmd: list[str], default: str = "unknown") -> str:
    try:
        return run(cmd)
    except Exception:
        return default


def main() -> None:
    if not FINDINGS_PATH.exists():
        raise SystemExit(f"Missing {FINDINGS_PATH}. Run scanner first.")

    findings = json.loads(FINDINGS_PATH.read_text())
    exceptions = findings.get("exceptions", [])
    finding_items = findings.get("findings", [])

    # Pull allow/deny and reasons from artifacts if present (optional)
    reasons = []
    if REASONS_PATH.exists():
        # OPA -f json returns an array of result objects; we extract the first result expression value.
        payload = json.loads(REASONS_PATH.read_text())
        # payload example: [{"result":[{"expressions":[{"value":[...reasons...]}]}]}]
        try:
            reasons = payload[0]["result"][0]["expressions"][0]["value"]
        except Exception:
            reasons = []

    # Git metadata (best-effort)
    git_sha = safe_git(["git", "rev-parse", "HEAD"])
    git_branch = safe_git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    git_status = safe_git(["git", "status", "--porcelain"], default="")
    dirty = bool(git_status)

    # If in GitHub Actions, these may exist
    github = {
        "repo": os.getenv("GITHUB_REPOSITORY"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_number": os.getenv("GITHUB_RUN_NUMBER"),
        "workflow": os.getenv("GITHUB_WORKFLOW"),
        "actor": os.getenv("GITHUB_ACTOR"),
        "ref": os.getenv("GITHUB_REF"),
        "sha": os.getenv("GITHUB_SHA"),
    }

    # Timestamp in UTC
    ts = datetime.now(timezone.utc).isoformat()

    record = {
        "timestamp_utc": ts,
        "project": findings.get("project"),
        "manifest_path": findings.get("manifest_path"),
        "git": {
            "sha": git_sha,
            "branch": git_branch,
            "dirty": dirty,
        },
        "github": github,
        "summary": {
            "finding_count": len(finding_items),
            "pii_finding_count": sum(1 for f in finding_items if f.get("type") == "pii_detected"),
            "missing_meta_count": sum(1 for f in finding_items if f.get("type") == "missing_meta"),
        },
        "exceptions_used": exceptions,
        "reasons": reasons,
        "findings": finding_items,  # keep for MVP; later you can store just hashes/ids
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"Wrote evidence record to {EVIDENCE_FILE}")


if __name__ == "__main__":
    main()
