#!/usr/bin/env python3
"""OpenClaw OpenAI paid-API guard.

Scans the global OpenClaw config, cron jobs, and workspace config-like files for
OpenAI Platform/API-style model references (`openai/...`) that bypass the
Codex OAuth-prefixed provider (`openai-codex/...`).

Exit codes:
  0 = no paid-API findings
  2 = warnings found
  1 = guard failure
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

PAID_MODEL_PREFIXES = ("openai/",)
CODEX_PREFIX = "openai-codex/"
DEFAULT_ROOT = Path.home() / ".openclaw"

EXCLUDED_DIR_NAMES = {
    ".git",
    "logs",
    "media",
    "browser",
    "tasks",
    "delivery-queue",
    "completions",
    "node_modules",
    "artifacts",
    "reports",
    "state",
    "memory",
    "ops\\billing-guard",
    "__pycache__",
}
EXCLUDED_FILE_MARKERS = (
    ".bak",
    ".backup",
    ".clobbered.",
    ".rejected.",
    ".deleted.",
    ".reset.",
    ".trajectory",
    "sessions.json",
    "MEMORY.md",
    "SHARED_FROM_MAIN.md",
    "openai_paid_api_guard.py",
)
SCAN_SUFFIXES = {".json", ".jsonc", ".md", ".txt", ".ps1", ".py", ".js", ".mjs", ".ts"}


@dataclass
class Finding:
    severity: str
    path: str
    location: str
    value: str
    reason: str


def is_paid_model(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(PAID_MODEL_PREFIXES) and not value.startswith(CODEX_PREFIX)


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def walk_json(obj: Any, path: list[str]) -> Iterable[tuple[list[str], Any]]:
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_json(v, path + [str(k)])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_json(v, path + [str(i)])


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def scan_openclaw_json(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    path = root / "openclaw.json"
    data = load_json(path)
    if data is None:
        findings.append(Finding("ERROR", relpath(path, root), "file", "unreadable", "Could not parse openclaw.json"))
        return findings

    for jpath, value in walk_json(data, []):
        joined = ".".join(jpath)
        if is_paid_model(value):
            findings.append(Finding(
                "WARN",
                relpath(path, root),
                joined,
                value,
                "OpenAI Platform/API model prefix detected; use openai-codex/... for Codex OAuth models or Ollama/local.",
            ))

    memory = data.get("agents", {}).get("defaults", {}).get("memorySearch", {})
    if isinstance(memory, dict) and memory.get("enabled") is not False and memory.get("provider") == "openai":
        findings.append(Finding(
            "WARN",
            relpath(path, root),
            "agents.defaults.memorySearch",
            f"provider=openai model={memory.get('model')}",
            "Memory semantic search uses OpenAI embeddings; this may bill OpenAI Platform usage and is not Codex OAuth.",
        ))
    return findings


def scan_cron(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    path = root / "cron" / "jobs.json"
    data = load_json(path)
    if data is None:
        findings.append(Finding("ERROR", relpath(path, root), "file", "unreadable", "Could not parse cron/jobs.json"))
        return findings
    for idx, job in enumerate(data.get("jobs", [])):
        if not isinstance(job, dict):
            continue
        model = job.get("payload", {}).get("model") if isinstance(job.get("payload"), dict) else None
        if is_paid_model(model):
            enabled = job.get("enabled") is not False
            findings.append(Finding(
                "WARN" if enabled else "INFO",
                relpath(path, root),
                f"jobs[{idx}] {job.get('name')} payload.model",
                model,
                f"Cron job {'enabled' if enabled else 'disabled'} with OpenAI Platform/API model prefix.",
            ))
    return findings


def should_scan_file(path: Path, root: Path) -> bool:
    rel_tuple = path.relative_to(root).parts if path.is_relative_to(root) else path.parts
    rel_parts = set(rel_tuple)
    if rel_parts & EXCLUDED_DIR_NAMES:
        return False
    rel_string = str(Path(*rel_tuple))
    if "workspace-ocbuilder\\ops\\billing-guard" in rel_string or "workspace-ocbuilder/ops/billing-guard" in rel_string:
        return False
    name = path.name
    if any(marker in name for marker in EXCLUDED_FILE_MARKERS):
        return False
    return path.suffix.lower() in SCAN_SUFFIXES


def scan_workspace_text(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for base in root.glob("workspace*"):
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or not should_scan_file(path, root):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for needle in PAID_MODEL_PREFIXES:
                if needle not in text:
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if needle in line and CODEX_PREFIX not in line:
                        findings.append(Finding(
                            "INFO",
                            relpath(path, root),
                            f"line {lineno}",
                            line.strip()[:220],
                            "Workspace text references an OpenAI Platform/API prefix; review if this is live config/prompt code.",
                        ))
                break
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Warn when OpenAI paid/API model paths are configured in OpenClaw.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="OpenClaw root directory")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--write-report", default=None, help="Optional path for JSON report")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    findings: list[Finding] = []
    try:
        findings.extend(scan_openclaw_json(root))
        findings.extend(scan_cron(root))
        findings.extend(scan_workspace_text(root))
    except Exception as exc:
        findings.append(Finding("ERROR", str(root), "guard", repr(exc), "Guard failed unexpectedly"))

    report = {
        "ok": not any(f.severity in {"WARN", "ERROR"} for f in findings),
        "root": str(root),
        "findings": [asdict(f) for f in findings],
    }

    if args.write_report:
        out = Path(args.write_report).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if report["ok"]:
            print("PASS: no OpenAI paid/API model references found outside Codex OAuth prefixes.")
        else:
            print("WARNING: possible OpenAI paid/API usage found")
            for f in findings:
                print(f"- {f.severity}: {f.path} :: {f.location} :: {f.value}")
                print(f"  {f.reason}")

    if any(f.severity == "ERROR" for f in findings):
        return 1
    if any(f.severity == "WARN" for f in findings):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
