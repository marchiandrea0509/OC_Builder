#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class HealthError(RuntimeError):
    pass


def git_binary() -> str:
    for candidate in ("git", "git.exe", "git.cmd"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise HealthError("Git CLI not found in PATH")


def run_git(args: list[str], cwd: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [git_binary(), *args]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise HealthError(
            f"Git command failed ({' '.join(cmd)}) in {cwd}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise HealthError(f"JSON config must be an object: {path}")
    return data


def git_dir(path: Path) -> Path:
    return path / ".git"


def branch_name(path: Path) -> str:
    result = run_git(["branch", "--show-current"], cwd=str(path), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def origin_url(path: Path) -> str:
    result = run_git(["remote", "get-url", "origin"], cwd=str(path), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def in_progress_state(path: Path) -> list[str]:
    g = git_dir(path)
    checks = {
        "MERGE_HEAD": g / "MERGE_HEAD",
        "rebase-merge": g / "rebase-merge",
        "rebase-apply": g / "rebase-apply",
        "CHERRY_PICK_HEAD": g / "CHERRY_PICK_HEAD",
        "REVERT_HEAD": g / "REVERT_HEAD",
        "BISECT_LOG": g / "BISECT_LOG",
    }
    return [name for name, p in checks.items() if p.exists()]


def fetch_origin(path: Path) -> None:
    run_git(["fetch", "origin", "--prune"], cwd=str(path))


def upstream_branch(path: Path) -> str:
    result = run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], cwd=str(path), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def remote_branch_exists(path: Path, branch: str) -> bool:
    result = run_git(["ls-remote", "--heads", "origin", branch], cwd=str(path), check=False)
    return bool(result.stdout.strip())


def ahead_behind(path: Path, upstream: str) -> tuple[int, int]:
    result = run_git(["rev-list", "--left-right", "--count", f"{upstream}...HEAD"], cwd=str(path), check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return 0, 0
    behind, ahead = result.stdout.strip().split()
    return int(behind), int(ahead)


def status_counts(path: Path) -> dict[str, int]:
    result = run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=str(path), check=False)
    counts = {"dirty": 0, "untracked": 0, "modified": 0, "deleted": 0, "renamed": 0, "copied": 0, "ignored": 0}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        counts["dirty"] += 1
        code = line[:2]
        if code == "??":
            counts["untracked"] += 1
        if "M" in code:
            counts["modified"] += 1
        if "D" in code:
            counts["deleted"] += 1
        if "R" in code:
            counts["renamed"] += 1
        if "C" in code:
            counts["copied"] += 1
        if code == "!!":
            counts["ignored"] += 1
    return counts


def build_markdown(entries: list[dict[str, Any]], generated_at: str, dirty_threshold: int, untracked_threshold: int) -> str:
    lines = [
        "# Workspace Monthly Health",
        f"Generated: {generated_at}",
        f"Dirty threshold: {dirty_threshold}",
        f"Untracked threshold: {untracked_threshold}",
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
        lines.append(f"  - Dirty: {entry.get('dirtyCount', 0)}")
        lines.append(f"  - Untracked: {entry.get('untrackedCount', 0)}")
        lines.append(f"  - Behind: {entry.get('behind', 0)}")
        lines.append(f"  - Ahead: {entry.get('ahead', 0)}")
        if entry.get("notes"):
            for note in entry["notes"]:
                lines.append(f"  - Note: {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Monthly read-only health audit for workspace repos")
    parser.add_argument("--config", required=True)
    parser.add_argument("--policy", required=False)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        config = load_json(Path(args.config))
        policy = load_json(Path(args.policy)) if args.policy else {}

        targets = config.get("targets")
        if not isinstance(targets, list):
            raise HealthError("Config must contain a 'targets' array")

        dirty_threshold = int(policy.get("dirtyAttentionThreshold", 25))
        untracked_threshold = int(policy.get("untrackedAttentionThreshold", 25))

        generated_dir = Path(__file__).resolve().parent / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        json_output = generated_dir / "workspace_monthly_health.json"
        md_output = generated_dir / "workspace_monthly_health.md"

        results: list[dict[str, Any]] = []
        attention: list[str] = []
        overall = "PASS"
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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
                "dirtyCount": 0,
                "untrackedCount": 0,
                "behind": 0,
                "ahead": 0,
            }

            try:
                if not path.exists():
                    raise HealthError(f"Path does not exist: {path}")
                if not git_dir(path).exists():
                    raise HealthError("Not a Git repository")

                branch = branch_name(path)
                origin = origin_url(path)
                target_result["branch"] = branch
                target_result["origin"] = origin

                if not branch:
                    raise HealthError("Detached HEAD or no current branch")
                if not origin:
                    raise HealthError("No origin remote configured")

                in_progress = in_progress_state(path)
                if in_progress:
                    raise HealthError(f"Git operation already in progress: {', '.join(in_progress)}")

                fetch_origin(path)

                upstream = upstream_branch(path)
                if not upstream:
                    if remote_branch_exists(path, branch):
                        target_result["notes"].append("upstream tracking missing but remote branch exists")
                    else:
                        raise HealthError("Remote branch missing; repository cannot be validated against origin")
                else:
                    behind, ahead = ahead_behind(path, upstream)
                    target_result["behind"] = behind
                    target_result["ahead"] = ahead
                    if behind > 0 and ahead > 0:
                        raise HealthError(f"Branch diverged from upstream ({behind} behind, {ahead} ahead)")
                    if behind > 0:
                        raise HealthError(f"Branch is behind upstream by {behind} commit(s)")
                    if ahead > 0:
                        target_result["notes"].append(f"{ahead} local commit(s) ahead of upstream")

                counts = status_counts(path)
                target_result["dirtyCount"] = counts["dirty"]
                target_result["untrackedCount"] = counts["untracked"]

                if counts["dirty"] or counts["untracked"]:
                    target_result["notes"].append(f"{counts['dirty']} dirty / {counts['untracked']} untracked file(s)")

                if counts["dirty"] >= dirty_threshold:
                    raise HealthError(f"Dirty working tree has {counts['dirty']} change(s), above threshold {dirty_threshold}")
                if counts["untracked"] >= untracked_threshold:
                    raise HealthError(f"Untracked files count {counts['untracked']} is above threshold {untracked_threshold}")

            except Exception as exc:  # noqa: BLE001
                target_result["status"] = "FAIL"
                target_result["error"] = str(exc)
                attention.append(f"{name}: {exc}")
                overall = "FAIL"

            results.append(target_result)

        payload = {
            "generatedAt": generated_at,
            "overall": overall,
            "dirtyAttentionThreshold": dirty_threshold,
            "untrackedAttentionThreshold": untracked_threshold,
            "targets": results,
            "attention": attention,
            "needsAttention": bool(attention),
        }

        json_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md_output.write_text(build_markdown(results, generated_at, dirty_threshold, untracked_threshold), encoding="utf-8")

        print(json.dumps(payload, indent=2) if args.json else json.dumps(payload))
        return 0 if overall == "PASS" else 1
    except Exception as exc:  # noqa: BLE001
        report = {"overall": "FAIL", "error": str(exc), "needsAttention": True, "attention": [str(exc)]}
        print(json.dumps(report, indent=2) if args.json else json.dumps(report))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
