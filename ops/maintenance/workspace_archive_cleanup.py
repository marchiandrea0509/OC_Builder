#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class CleanupError(RuntimeError):
    pass


def git_binary() -> str:
    for candidate in ("git", "git.exe", "git.cmd"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise CleanupError("Git CLI not found in PATH")


def run_git(args: list[str], cwd: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [git_binary(), *args]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise CleanupError(
            f"Git command failed ({' '.join(cmd)}) in {cwd}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CleanupError(f"JSON config must be an object: {path}")
    return data


def git_dir(path: Path) -> Path:
    return path / ".git"


def tracked_files(path: Path) -> set[str]:
    result = run_git(["ls-files"], cwd=str(path), check=False)
    if result.returncode != 0:
        return set()
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def disk_age_cutoff(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def is_old_file(path: Path, cutoff: datetime) -> bool:
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime <= cutoff


def format_bytes(num: int) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024.0
    return f"{num}B"


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for idx in range(1, 1000):
        candidate = parent / f"{stem}__{idx}{suffix}"
        if not candidate.exists():
            return candidate
    raise CleanupError(f"Could not find unique archive destination for {path}")


def remove_empty_dirs(root: Path) -> int:
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p == root:
            continue
        if not dirnames and not filenames:
            try:
                p.rmdir()
                removed += 1
            except OSError:
                pass
    return removed


def build_markdown(entries: list[dict[str, Any]], generated_at: str, age_days: int) -> str:
    lines = [
        "# Workspace Archive Cleanup",
        f"Generated: {generated_at}",
        f"Archive age threshold: {age_days} days",
        "",
    ]
    for entry in entries:
        lines.append(f"- **{entry['name']}**")
        lines.append(f"  - Path: `{entry['path']}`")
        lines.append(f"  - Status: {entry['status']}")
        lines.append(f"  - Archived: {entry.get('archivedCount', 0)} files / {format_bytes(entry.get('archivedBytes', 0))}")
        lines.append(f"  - Skipped tracked: {entry.get('skippedTrackedCount', 0)}")
        lines.append(f"  - Removed empty dirs: {entry.get('removedEmptyDirs', 0)}")
        if entry.get("notes"):
            for note in entry["notes"]:
                lines.append(f"  - Note: {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive old untracked files from disposable workspace folders")
    parser.add_argument("--config", required=True)
    parser.add_argument("--policy", required=False)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        config = load_json(Path(args.config))
        policy = load_json(Path(args.policy)) if args.policy else {}

        targets = config.get("targets")
        if not isinstance(targets, list):
            raise CleanupError("Config must contain a 'targets' array")

        age_days = int(policy.get("archiveAgeDays", 30))
        archive_root = Path(str(policy.get("archiveRoot") or r"C:\Users\anmar\.openclaw\workspace-archives"))
        candidate_dirs = [str(item) for item in (policy.get("candidateDirs") or ["logs", "log", "tmp", "temp", "generated", "reports", "artifacts", "cache"])]
        cutoff = disk_age_cutoff(age_days)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m")

        generated_dir = Path(__file__).resolve().parent / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        json_output = generated_dir / "workspace_archive_cleanup.json"
        md_output = generated_dir / "workspace_archive_cleanup.md"

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
                "archivedCount": 0,
                "archivedBytes": 0,
                "skippedTrackedCount": 0,
                "removedEmptyDirs": 0,
            }

            try:
                if not path.exists():
                    raise CleanupError(f"Path does not exist: {path}")

                tracked = tracked_files(path) if git_dir(path).exists() else set()

                for rel_dir in candidate_dirs:
                    source_root = path / rel_dir
                    if not source_root.exists() or not source_root.is_dir():
                        continue

                    for file_path in source_root.rglob("*"):
                        if not file_path.is_file():
                            continue
                        if not is_old_file(file_path, cutoff):
                            continue

                        rel = file_path.relative_to(path).as_posix()
                        if tracked and rel in tracked:
                            target_result["skippedTrackedCount"] += 1
                            continue

                        archive_path = unique_destination(archive_root / name / stamp / rel)
                        archive_path.parent.mkdir(parents=True, exist_ok=True)
                        size = file_path.stat().st_size
                        shutil.move(str(file_path), str(archive_path))
                        target_result["archivedCount"] += 1
                        target_result["archivedBytes"] += size

                    target_result["removedEmptyDirs"] += remove_empty_dirs(source_root)

                if target_result["archivedCount"]:
                    target_result["notes"].append(f"archived {target_result['archivedCount']} old file(s)")
                else:
                    target_result["notes"].append("no old disposable files needed archiving")

                if target_result["skippedTrackedCount"]:
                    target_result["notes"].append(f"skipped {target_result['skippedTrackedCount']} tracked file(s)")

            except Exception as exc:  # noqa: BLE001
                target_result["status"] = "FAIL"
                target_result["error"] = str(exc)
                attention.append(f"{name}: {exc}")
                overall = "FAIL"

            results.append(target_result)

        payload = {
            "generatedAt": generated_at,
            "overall": overall,
            "archiveAgeDays": age_days,
            "archiveRoot": str(archive_root),
            "targets": results,
            "attention": attention,
            "needsAttention": bool(attention),
        }

        json_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md_output.write_text(build_markdown(results, generated_at, age_days), encoding="utf-8")

        print(json.dumps(payload, indent=2) if args.json else json.dumps(payload))
        return 0 if overall == "PASS" else 1
    except Exception as exc:  # noqa: BLE001
        report = {"overall": "FAIL", "error": str(exc), "needsAttention": True, "attention": [str(exc)]}
        print(json.dumps(report, indent=2) if args.json else json.dumps(report))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
