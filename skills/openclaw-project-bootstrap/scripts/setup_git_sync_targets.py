#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class SetupError(RuntimeError):
    pass


def git_binary() -> str:
    for candidate in ("git", "git.exe", "git.cmd"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SetupError("Git CLI not found in PATH")


def run_git(args: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [git_binary(), *args]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise SetupError(
            f"Git command failed ({' '.join(cmd)}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("targets"), list):
        raise SetupError("Config must be a JSON object with a 'targets' array")
    return data


def ensure_repo(path: Path, init_if_missing: bool) -> tuple[bool, bool]:
    git_dir = path / ".git"
    if git_dir.exists():
        return True, False
    if not init_if_missing:
        return False, False
    run_git(["init"], cwd=str(path))
    return True, True


def current_branch(path: Path) -> str:
    result = run_git(["branch", "--show-current"], cwd=str(path), check=False)
    return result.stdout.strip()


def ensure_origin(path: Path, url: str) -> str:
    result = run_git(["remote", "get-url", "origin"], cwd=str(path), check=False)
    current = result.stdout.strip() if result.returncode == 0 else ""
    if not current:
        run_git(["remote", "add", "origin", url], cwd=str(path))
        return "added"
    if current != url:
        run_git(["remote", "set-url", "origin", url], cwd=str(path))
        return "updated"
    return "unchanged"


def ensure_local_identity(path: Path, name: str, email: str) -> list[str]:
    changes: list[str] = []
    current_name = run_git(["config", "--local", "user.name"], cwd=str(path), check=False).stdout.strip()
    current_email = run_git(["config", "--local", "user.email"], cwd=str(path), check=False).stdout.strip()
    if not current_name:
        run_git(["config", "--local", "user.name", name], cwd=str(path))
        changes.append("user.name")
    if not current_email:
        run_git(["config", "--local", "user.email", email], cwd=str(path))
        changes.append("user.email")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up Git remotes/identity for workspace sync targets")
    parser.add_argument("--config", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        config = load_config(Path(args.config))
        author = config.get("author") or {}
        author_name = str(author.get("name") or "OpenClaw")
        author_email = str(author.get("email") or "openclaw@local")
        results: list[dict[str, Any]] = []
        overall = "PASS"

        for target in config["targets"]:
            name = str(target["name"])
            path = Path(str(target["path"]))
            origin = str(target["origin"])
            init_if_missing = bool(target.get("initIfMissingRepo", False))
            target_result: dict[str, Any] = {
                "name": name,
                "path": str(path),
                "origin": origin,
                "status": "PASS",
                "notes": [],
            }
            try:
                if not path.exists():
                    raise SetupError(f"Path does not exist: {path}")
                repo_exists, repo_initialized = ensure_repo(path, init_if_missing)
                if not repo_exists:
                    raise SetupError(f"Not a Git repo and initIfMissingRepo=false: {path}")
                if repo_initialized:
                    target_result["notes"].append("git repo initialized")
                remote_change = ensure_origin(path, origin)
                if remote_change != "unchanged":
                    target_result["notes"].append(f"origin {remote_change}")
                identity_changes = ensure_local_identity(path, author_name, author_email)
                for change in identity_changes:
                    target_result["notes"].append(f"local {change} set")
                branch = current_branch(path)
                target_result["branch"] = branch or None
            except Exception as exc:  # noqa: BLE001
                target_result["status"] = "FAIL"
                target_result["error"] = str(exc)
                overall = "FAIL"
            results.append(target_result)

        report = {
            "overall": overall,
            "author": {"name": author_name, "email": author_email},
            "targets": results,
        }
        print(json.dumps(report, indent=2) if args.json else json.dumps(report))
        return 0 if overall == "PASS" else 1
    except Exception as exc:  # noqa: BLE001
        report = {"overall": "FAIL", "error": str(exc)}
        print(json.dumps(report, indent=2) if args.json else json.dumps(report))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
