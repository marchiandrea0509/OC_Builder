#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class SyncError(RuntimeError):
    pass


def git_binary() -> str:
    for candidate in ("git", "git.exe", "git.cmd"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SyncError("Git CLI not found in PATH")


def run_git(args: list[str], cwd: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [git_binary(), *args]
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=merged_env)
    if check and result.returncode != 0:
        raise SyncError(
            f"Git command failed ({' '.join(cmd)}) in {cwd}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("targets"), list):
        raise SyncError("Config must be a JSON object with a 'targets' array")
    return data


def git_dir(path: Path) -> Path:
    return path / ".git"


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


def branch_name(path: Path) -> str:
    return run_git(["branch", "--show-current"], cwd=str(path)).stdout.strip()


def origin_url(path: Path) -> str:
    result = run_git(["remote", "get-url", "origin"], cwd=str(path), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def working_changes(path: Path) -> list[str]:
    result = run_git(["status", "--porcelain"], cwd=str(path))
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines


def fetch_origin(path: Path) -> None:
    run_git(["fetch", "origin", "--prune"], cwd=str(path))


def upstream_branch(path: Path) -> str:
    result = run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], cwd=str(path), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def remote_branch_exists(path: Path, branch: str) -> bool:
    result = run_git(["ls-remote", "--heads", "origin", branch], cwd=str(path), check=False)
    return bool(result.stdout.strip())


def set_upstream(path: Path, branch: str) -> None:
    run_git(["branch", "--set-upstream-to", f"origin/{branch}", branch], cwd=str(path))


def ahead_behind(path: Path, upstream: str) -> tuple[int, int]:
    result = run_git(["rev-list", "--left-right", "--count", f"{upstream}...HEAD"], cwd=str(path))
    left, right = result.stdout.strip().split()
    return int(left), int(right)


def commit_all(path: Path, message: str, author_name: str, author_email: str) -> bool:
    run_git(["add", "-A"], cwd=str(path))
    staged = run_git(["diff", "--cached", "--name-only"], cwd=str(path)).stdout.strip()
    if not staged:
        return False
    env = {
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
    }
    run_git(["commit", "-m", message], cwd=str(path), env=env)
    return True


def push_branch(path: Path, branch: str, set_upstream_flag: bool) -> None:
    args = ["push"]
    if set_upstream_flag:
        args.extend(["-u", "origin", branch])
    run_git(args, cwd=str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely commit/push a set of Git workspaces")
    parser.add_argument("--config", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        config = load_config(Path(args.config))
        author = config.get("author") or {}
        author_name = str(author.get("name") or "OpenClaw")
        author_email = str(author.get("email") or "openclaw@local")
        commit_message = str(config.get("commitMessage") or "chore(sync): periodic workspace checkpoint")
        results: list[dict[str, Any]] = []
        attention: list[str] = []
        overall = "PASS"

        for target in config["targets"]:
            name = str(target["name"])
            path = Path(str(target["path"]))
            target_result: dict[str, Any] = {
                "name": name,
                "path": str(path),
                "status": "PASS",
                "notes": [],
                "committed": False,
                "pushed": False,
            }
            try:
                if not path.exists():
                    raise SyncError(f"Path does not exist: {path}")
                if not git_dir(path).exists():
                    raise SyncError("Not a Git repository")
                branch = branch_name(path)
                if not branch:
                    raise SyncError("Detached HEAD or no current branch")
                target_result["branch"] = branch
                origin = origin_url(path)
                if not origin:
                    raise SyncError("No origin remote configured")
                target_result["origin"] = origin
                in_progress = in_progress_state(path)
                if in_progress:
                    raise SyncError(f"Git operation already in progress: {', '.join(in_progress)}")

                changes = working_changes(path)
                target_result["changeCount"] = len(changes)
                if changes:
                    target_result["notes"].append(f"{len(changes)} working-tree changes detected")

                fetch_origin(path)
                upstream = upstream_branch(path)
                set_upstream_on_push = False
                if not upstream:
                    if remote_branch_exists(path, branch):
                        set_upstream(path, branch)
                        upstream = f"origin/{branch}"
                        target_result["notes"].append("upstream tracking configured")
                    else:
                        set_upstream_on_push = True
                        target_result["notes"].append("remote branch missing; first push will set upstream")

                behind = ahead = 0
                if upstream:
                    behind, ahead = ahead_behind(path, upstream)
                    target_result["behind"] = behind
                    target_result["ahead"] = ahead
                    if behind > 0 and ahead > 0:
                        raise SyncError(f"Branch diverged from upstream ({behind} behind, {ahead} ahead)")
                    if behind > 0 and ahead == 0:
                        raise SyncError(f"Branch is behind upstream by {behind} commit(s); refusing auto-push")

                if changes:
                    committed = commit_all(path, commit_message, author_name, author_email)
                    target_result["committed"] = committed
                    if committed:
                        target_result["notes"].append("commit created")
                        if upstream:
                            behind, ahead = ahead_behind(path, upstream)
                            target_result["behind"] = behind
                            target_result["ahead"] = ahead

                should_push = False
                if set_upstream_on_push:
                    should_push = True
                elif upstream and target_result.get("ahead", 0) > 0:
                    should_push = True

                if should_push:
                    push_branch(path, branch, set_upstream_on_push)
                    target_result["pushed"] = True
                    target_result["notes"].append("push completed")
                elif not changes:
                    target_result["notes"].append("no changes to sync")
            except Exception as exc:  # noqa: BLE001
                target_result["status"] = "FAIL"
                target_result["error"] = str(exc)
                attention.append(f"{name}: {exc}")
                overall = "FAIL"
            results.append(target_result)

        report = {
            "overall": overall,
            "author": {"name": author_name, "email": author_email},
            "commitMessage": commit_message,
            "targets": results,
            "attention": attention,
            "needsAttention": bool(attention),
        }
        print(json.dumps(report, indent=2) if args.json else json.dumps(report))
        return 0 if overall == "PASS" else 1
    except Exception as exc:  # noqa: BLE001
        report = {"overall": "FAIL", "error": str(exc), "needsAttention": True, "attention": [str(exc)]}
        print(json.dumps(report, indent=2) if args.json else json.dumps(report))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
