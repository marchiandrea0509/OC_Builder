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


def openclaw_binary() -> str:
    for candidate in ("openclaw", "openclaw.cmd", "openclaw.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise MaintenanceError("OpenClaw CLI not found in PATH")


def run_command(
    args: list[str],
    cwd: str | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
    timeout: int | None = 30,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=merged_env,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise MaintenanceError(
            f"Command failed ({' '.join(args)}) in {cwd or os.getcwd()}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def run_git(args: list[str], cwd: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run_command([git_binary(), *args], cwd=cwd, check=check, env=env)


def parse_json_output(text: str | None) -> Any:
    if text is None:
        raise MaintenanceError("Expected JSON output but command returned no stdout")
    text = text.strip()
    if not text:
        raise MaintenanceError("Expected JSON output but command returned empty stdout")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for idx, ch in enumerate(text):
            if ch not in "[{":
                continue
            try:
                obj, _end = decoder.raw_decode(text[idx:])
                return obj
            except json.JSONDecodeError:
                continue
        raise MaintenanceError(f"Could not parse JSON output:\n{text}")


def openclaw_json(*args: str) -> Any:
    result = run_command([openclaw_binary(), *args])
    return parse_json_output(result.stdout)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise MaintenanceError(f"JSON config must be an object: {path}")
    return data


def load_target_list(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        targets = data.get("targets")
        if not isinstance(targets, list):
            raise MaintenanceError(f"Config must contain a 'targets' array: {path}")
        data = targets
    if not isinstance(data, list):
        raise MaintenanceError(f"JSON config must be an array or object with 'targets': {path}")
    records: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise MaintenanceError(f"Target entry must be an object: {path}")
        records.append(item)
    return records


def resolve_path(base_dir: Path, raw_value: Any) -> Path:
    value = Path(str(raw_value))
    if value.is_absolute():
        return value
    return (base_dir / value).resolve()


def normalize_target_paths(target: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    normalized = dict(target)
    for key in ("path", "contextPath", "exportPath", "historyPath", "sourcePath"):
        value = normalized.get(key)
        if isinstance(value, str) and value.strip():
            normalized[key] = str(resolve_path(base_dir, value))
    return normalized


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


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


def disk_usage_percent(path: Path) -> float:
    usage = shutil.disk_usage(path)
    if usage.total <= 0:
        return 0.0
    return round((usage.used / usage.total) * 100.0, 2)


def compact_repo(path: Path) -> None:
    run_git(["reflog", "expire", "--expire=30.days.ago", "--all"], cwd=str(path), check=False)
    run_git(["gc", "--prune=now", "--quiet"], cwd=str(path))


def discord_bindings() -> list[dict[str, Any]]:
    bindings = openclaw_json("agents", "bindings", "--json")
    if not isinstance(bindings, list):
        raise MaintenanceError("Unexpected response for openclaw agents bindings --json")
    return bindings


def find_discord_binding(
    bindings: list[dict[str, Any]],
    guild_id: str | None,
    channel_id: str | None,
    account_id: str | None,
) -> dict[str, Any] | None:
    for binding in bindings:
        match = binding.get("match") or {}
        peer = match.get("peer") or {}
        if match.get("channel") != "discord":
            continue
        if guild_id and str(match.get("guildId")) != guild_id:
            continue
        if account_id and match.get("accountId") not in (None, account_id):
            continue
        if peer.get("kind") != "channel":
            continue
        if channel_id and str(peer.get("id")) != channel_id:
            continue
        return binding
    return None


def summarize_context_export(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise MaintenanceError(f"Path does not exist: {path}")

    summary: dict[str, Any] = {
        "sourceType": "unknown",
        "contextMessageCount": 0,
        "contextChars": 0,
        "contextBytes": 0,
        "notes": [],
    }

    if path.is_dir():
        files = [item for item in path.rglob("*") if item.is_file()]
        summary["sourceType"] = "directory"
        summary["contextMessageCount"] = len(files)
        summary["contextBytes"] = sum(item.stat().st_size for item in files)
        summary["contextChars"] = summary["contextBytes"]
        summary["notes"].append(f"{len(files)} file(s) in exported context directory")
        return summary

    summary["contextBytes"] = path.stat().st_size

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        summary["sourceType"] = "json"
        if isinstance(data, list):
            summary["contextMessageCount"] = len(data)
            summary["contextChars"] = sum(len(stable_json(item)) for item in data)
            return summary
        if isinstance(data, dict):
            for key in ("messages", "history", "entries", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    summary["contextMessageCount"] = len(value)
                    summary["contextChars"] = sum(len(stable_json(item)) for item in value)
                    return summary
            summary["contextMessageCount"] = 1
            summary["contextChars"] = len(stable_json(data))
            return summary
        summary["contextMessageCount"] = 1
        summary["contextChars"] = len(stable_json(data))
        return summary

    text = path.read_text(encoding="utf-8", errors="replace")
    summary["sourceType"] = "text"
    summary["contextMessageCount"] = len([line for line in text.splitlines() if line.strip()])
    summary["contextChars"] = len(text)
    return summary


def target_kind(target: dict[str, Any]) -> str:
    kind = str(target.get("kind") or "").strip().lower()
    if kind:
        return kind
    if any(key in target for key in ("threadId", "historyPath", "contextPath", "exportPath", "sourcePath")):
        return "discord-thread"
    if target.get("guildId") and target.get("channelId"):
        return "discord-room"
    return "git"


def build_markdown(entries: list[dict[str, Any]], generated_at: str, threshold: float) -> str:
    lines = [
        "# Workspace Index",
        f"Generated: {generated_at}",
        f"Compact threshold: {threshold:.0f}%",
        "",
    ]
    for entry in entries:
        lines.append(f"- **{entry['name']}**")
        if entry.get("kind"):
            lines.append(f"  - Kind: `{entry['kind']}`")
        lines.append(f"  - Path: `{entry['path']}`")
        lines.append(f"  - Status: {entry['status']}")
        if entry.get("branch"):
            lines.append(f"  - Branch: `{entry['branch']}`")
        if entry.get("origin"):
            lines.append(f"  - Origin: `{entry['origin']}`")
        if entry.get("guildId"):
            lines.append(f"  - Guild: `{entry['guildId']}`")
        if entry.get("channelId"):
            lines.append(f"  - Channel: `{entry['channelId']}`")
        if entry.get("threadId"):
            lines.append(f"  - Thread: `{entry['threadId']}`")
        if entry.get("bindingOwner"):
            lines.append(f"  - Discord route owner: `{entry['bindingOwner']}`")
        if entry.get("changeCount") is not None:
            lines.append(f"  - Changes: {entry.get('changeCount', 0)}")
        if entry.get("diskUsagePercent") is not None:
            lines.append(f"  - Disk use: {entry.get('diskUsagePercent', 0.0):.2f}%")
        if entry.get("contextMessageCount") is not None:
            lines.append(f"  - Context messages: {entry.get('contextMessageCount', 0)}")
        if entry.get("contextChars") is not None:
            lines.append(f"  - Context chars: {entry.get('contextChars', 0)}")
        lines.append(f"  - Compacted: {'yes' if entry.get('compacted') else 'no'}")
        if entry.get("notes"):
            for note in entry["notes"]:
                lines.append(f"  - Note: {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh workspace indexes and Discord context maintenance only when needed")
    parser.add_argument("--config", required=True)
    parser.add_argument("--policy", required=False)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        config_path = Path(args.config)
        config = load_json(config_path)
        policy_path = Path(args.policy) if args.policy else None
        policy = load_json(policy_path) if policy_path else {}

        targets = config.get("targets")
        if not isinstance(targets, list):
            raise MaintenanceError("Config must contain a 'targets' array")

        policy_base_dir = policy_path.parent if policy_path else config_path.parent
        threshold = float(policy.get("compactThresholdPercent", 82))
        index_output_name = str(policy.get("indexOutputFile", "workspace_index.json"))
        index_markdown_name = str(policy.get("indexMarkdownFile", "workspace_index.md"))
        discord_room_message_threshold = int(policy.get("discordRoomContextMessageThreshold", 500))
        discord_room_char_threshold = int(policy.get("discordRoomContextCharThreshold", 50000))
        discord_thread_message_threshold = int(policy.get("discordThreadContextMessageThreshold", 200))
        discord_thread_char_threshold = int(policy.get("discordThreadContextCharThreshold", 20000))

        extra_targets: list[dict[str, Any]] = []
        discord_targets_file = policy.get("discordTargetsFile")
        if isinstance(discord_targets_file, str) and discord_targets_file.strip():
            discord_targets_path = resolve_path(policy_base_dir, discord_targets_file)
            if discord_targets_path.exists():
                extra_targets.extend(normalize_target_paths(item, discord_targets_path.parent) for item in load_target_list(discord_targets_path))
            else:
                raise MaintenanceError(f"Discord targets file does not exist: {discord_targets_path}")
        if isinstance(policy.get("discordTargets"), list):
            inline_targets = policy["discordTargets"]
            for item in inline_targets:
                if not isinstance(item, dict):
                    raise MaintenanceError("Policy 'discordTargets' entries must be objects")
                extra_targets.append(normalize_target_paths(item, policy_base_dir))

        all_targets = [normalize_target_paths(item, config_path.parent) for item in targets if isinstance(item, dict)]
        if len(all_targets) != len(targets):
            raise MaintenanceError("Config 'targets' must contain only objects")
        all_targets.extend(extra_targets)

        script_dir = Path(__file__).resolve().parent
        generated_dir = script_dir / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        json_output = generated_dir / index_output_name
        md_output = generated_dir / index_markdown_name

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        results: list[dict[str, Any]] = []
        attention: list[str] = []
        overall = "PASS"
        bindings_cache: list[dict[str, Any]] | None = None

        for target in all_targets:
            kind = target_kind(target)
            name = str(target.get("name") or "unnamed")
            path = Path(str(target.get("path") or target.get("contextPath") or target.get("exportPath") or target.get("historyPath") or ""))
            target_result: dict[str, Any] = {
                "name": name,
                "kind": kind,
                "path": str(path),
                "status": "PASS",
                "notes": [],
                "compacted": False,
            }

            try:
                if kind == "git":
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

                elif kind in {"discord-room", "discord-thread", "discord"}:
                    guild_id = str(target.get("guildId") or target.get("discordGuildId") or "").strip() or None
                    channel_id = str(target.get("channelId") or target.get("discordChannelId") or "").strip() or None
                    thread_id = str(target.get("threadId") or "").strip() or None
                    account_id = str(target.get("accountId") or target.get("discordAccountId") or "").strip() or None
                    target_result["guildId"] = guild_id
                    target_result["channelId"] = channel_id
                    target_result["threadId"] = thread_id

                    if kind == "discord-room" and (not guild_id or not channel_id):
                        raise MaintenanceError("Discord room target requires guildId and channelId")
                    if kind == "discord-thread" and not thread_id:
                        raise MaintenanceError("Discord thread target requires threadId")

                    binding_source = target.get("bindingCheck", True)
                    if binding_source and guild_id and channel_id:
                        if bindings_cache is None:
                            bindings_cache = discord_bindings()
                        binding = find_discord_binding(bindings_cache, guild_id, channel_id, account_id)
                        desired_agent = str(target.get("agentId") or "").strip() or None
                        if binding is None:
                            if desired_agent:
                                raise MaintenanceError(f"Discord room binding missing for agent {desired_agent}")
                            target_result["notes"].append("discord room binding missing from live config")
                        else:
                            owner = str(binding.get("agentId") or "unknown")
                            target_result["bindingOwner"] = owner
                            if desired_agent and owner != desired_agent:
                                raise MaintenanceError(f"Discord room already bound to another agent: {owner}")
                            target_result["notes"].append(f"discord room binding verified for {owner}")

                    context_source = target.get("contextPath") or target.get("exportPath") or target.get("historyPath") or target.get("sourcePath")
                    if context_source:
                        context_path = Path(str(context_source))
                        summary = summarize_context_export(context_path)
                        target_result["contextSourceType"] = summary.get("sourceType")
                        target_result["contextMessageCount"] = summary.get("contextMessageCount", 0)
                        target_result["contextChars"] = summary.get("contextChars", 0)
                        target_result["contextBytes"] = summary.get("contextBytes", 0)
                        for note in summary.get("notes", []):
                            target_result["notes"].append(str(note))

                        message_limit = int(target.get("maxContextMessages") or (discord_thread_message_threshold if kind == "discord-thread" else discord_room_message_threshold))
                        char_limit = int(target.get("maxContextChars") or (discord_thread_char_threshold if kind == "discord-thread" else discord_room_char_threshold))
                        if message_limit > 0 and int(target_result["contextMessageCount"]) > message_limit:
                            raise MaintenanceError(
                                f"Discord context message count {target_result['contextMessageCount']} exceeds limit {message_limit}"
                            )
                        if char_limit > 0 and int(target_result["contextChars"]) > char_limit:
                            raise MaintenanceError(
                                f"Discord context size {target_result['contextChars']} chars exceeds limit {char_limit}"
                            )
                        target_result["notes"].append(
                            f"context export within limits ({target_result['contextMessageCount']} message(s), {target_result['contextChars']} chars)"
                        )
                    elif kind == "discord-thread":
                        raise MaintenanceError("Discord thread maintenance requires contextPath/exportPath/historyPath")
                    else:
                        target_result["notes"].append("discord room binding checked; no local context export configured")

                else:
                    raise MaintenanceError(f"Unsupported maintenance target kind: {kind}")

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
            "discordRoomContextMessageThreshold": discord_room_message_threshold,
            "discordRoomContextCharThreshold": discord_room_char_threshold,
            "discordThreadContextMessageThreshold": discord_thread_message_threshold,
            "discordThreadContextCharThreshold": discord_thread_char_threshold,
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
