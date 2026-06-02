#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MaintenanceError(RuntimeError):
    pass


def git_binary() -> str:
    for candidate in ("git", "git.exe", "git.cmd"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise MaintenanceError("Git CLI not found in PATH")


def run_git(args: list[str], cwd: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [git_binary(), *args]
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=merged_env)
    if check and result.returncode != 0:
        raise MaintenanceError(
            f"Git command failed ({' '.join(cmd)}) in {cwd}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise MaintenanceError(f"JSON config must be an object: {path}")
    return data


def git_dir(path: Path) -> Path:
    return path / ".git"


def branch_name(path: Path) -> str:
    result = run_git(["branch", "--show-current"], cwd=str(path), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def origin_url(path: Path) -> str:
    result = run_git(["remote", "get-url", "origin"], cwd=str(path), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def working_changes(path: Path) -> list[str]:
    result = run_git(["status", "--porcelain"], cwd=str(path))
    return [line for line in result.stdout.splitlines() if line.strip()]


def ahead_behind(path: Path, upstream: str) -> tuple[int, int]:
    result = run_git(["rev-list", "--left-right", "--count", f"{upstream}...HEAD"], cwd=str(path), check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return 0, 0
    left, right = result.stdout.strip().split()
    return int(left), int(right)


def disk_usage_percent(path: Path) -> float:
    usage = shutil.disk_usage(path)
    if usage.total <= 0:
        return 0.0
    return round((usage.used / usage.total) * 100.0, 2)


def compact_repo(path: Path) -> None:
    run_git(["reflog", "expire", "--expire=30.days.ago", "--all"], cwd=str(path), check=False)
    run_git(["gc", "--prune=now", "--quiet"], cwd=str(path))


def now_berlin_stamp() -> str:
    # Good enough for report artifacts; cron delivery handles local presentation.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_markdown(entries: list[dict[str, Any]], generated_at: str, threshold: float) -> str:
    lines = [
        "# Workspace Index",
        f"Generated: {generated_at}",
        f"Compact threshold: {threshold:.0f}%",
        "",
    ]
    for entry in entries:
        lines.append(f"- **{entry['name']}**")
        lines.append(f"  - Path: `{entry['path']}`")
        lines.append(f"  - Status: {entry['status']}")
        if entry.get("branch"):
            lines.append(f"  - Branch: `{entry['branch']}`")
        if entry.get("origin"):
            lines.append(f"  - Origin: `{entry['origin']}`")
        lines.append(f"  - Changes: {entry.get('changeCount', 0)}")
        lines.append(f"  - Disk use: {entry.get('diskUsagePercent', 0.0):.2f}%")
        lines.append(f"  - Compacted: {'yes' if entry.get('compacted') else 'no'}")
        if entry.get("notes"):
            for note in entry["notes"]:
                lines.append(f"  - Note: {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh workspace indexes and compact Git repos only when needed")
    parser.add_argument("--config", required=True)
    parser.add_argument("--policy", required=False)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        config_path = Path(args.config)
        config = load_json(config_path)
        policy = load_json(Path(args.policy)) if args.policy else {}

        targets = config.get("targets")
        if not isinstance(targets, list):
            raise MaintenanceError("Config must contain a 'targets' array")

        threshold = float(policy.get("compactThresholdPercent", 82))
        index_output_name = str(policy.get("indexOutputFile", "workspace_index.json"))
        index_markdown_name = str(policy.get("indexMarkdownFile", "workspace_index.md"))

        script_dir = Path(__file__).resolve().parent
        generated_dir = script_dir / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        json_output = generated_dir / index_output_name
        md_output = generated_dir / index_markdown_name

        generated_at = now_berlin_stamp()
        results: list[dict[str, Any]] = []
        attention: list[str] = []
        overall = "PASS"

        for target in targets:
            if not isinstance(target, dict):
                attention.append("Invalid target entry in config")
                overall = "FAIL"
                continue

            name = str(target.get("name") or "unnamed")
            path = Path(str(target.get("path") or ""))
            target_result: dict[str, Any] = {
                "name": name,
                "path": str(path),
                "status": "PASS",
                "notes": [],
                "compacted": False,
            }

            try:
                if not path.exists():
                    raise MaintenanceError(f"Path does not exist: {path}")
                if not git_dir(path).exists():
                    raise MaintenanceError("Not a Git repository")

                branch = branch_name(path)
                origin = origin_url(path)
                changes = working_changes(path)
                usage_percent = disk_usage_percent(path)

                target_result["branch"] = branch
                target_result["origin"] = origin
                target_result["changeCount"] = len(changes)
                target_result["diskUsagePercent"] = usage_percent

                if changes:
                    target_result["notes"].append(f"{len(changes)} working-tree changes detected")

                if usage_percent >= threshold:
                    compact_repo(path)
                    target_result["compacted"] = True
                    target_result["notes"].append(f"disk usage {usage_percent:.2f}% >= {threshold:.0f}%; compaction run")
                else:
                    target_result["notes"].append(f"disk usage {usage_percent:.2f}% below threshold")

            except Exception as exc:  # noqa: BLE001
                target_result["status"] = "FAIL"
                target_result["error"] = str(exc)
                attention.append(f"{name}: {exc}")
                overall = "FAIL"

            results.append(target_result)

        index_payload = {
            "generatedAt": generated_at,
            "overall": overall,
            "compactThresholdPercent": threshold,
            "targets": results,
            "attention": attention,
            "needsAttention": bool(attention),
        }

        json_output.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")
        md_output.write_text(build_markdown(results, generated_at, threshold), encoding="utf-8")

        print(json.dumps(index_payload, indent=2) if args.json else json.dumps(index_payload))
        return 0 if overall == "PASS" else 1
    except Exception as exc:  # noqa: BLE001
        report = {"overall": "FAIL", "error": str(exc), "needsAttention": True, "attention": [str(exc)]}
        print(json.dumps(report, indent=2) if args.json else json.dumps(report))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
