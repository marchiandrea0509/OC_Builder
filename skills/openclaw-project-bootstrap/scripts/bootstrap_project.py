#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_DIR / "assets"
PROJECT_STATE_TEMPLATE = ASSETS_DIR / "PROJECT_STATE.md"
SESSION_START_TEMPLATE = ASSETS_DIR / "SESSION_START.txt"
STANDARD_WORKSPACE_FILES = [
    "AGENTS.md",
    "SOUL.md",
    "USER.md",
    "TOOLS.md",
    "IDENTITY.md",
    "HEARTBEAT.md",
]


@dataclass
class Check:
    status: str
    message: str


class BootstrapError(RuntimeError):
    pass


class GatewayUnavailable(BootstrapError):
    pass


class FailureTracker:
    def __init__(self) -> None:
        self.current_blocker = "none"

    def add(self, checks: list[Check], status: str, message: str) -> None:
        checks.append(Check(status, message))
        if status == "FAIL" and self.current_blocker == "none":
            self.current_blocker = message


# ---------- basic helpers ----------


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_agent_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise BootstrapError("Could not derive a valid agent id from project name")
    return slug


def normalize_path(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def default_workspace_for(agent_id: str) -> Path:
    return Path.home() / ".openclaw" / f"workspace-{agent_id}"


def openclaw_binary() -> str:
    for candidate in ("openclaw", "openclaw.cmd", "openclaw.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise BootstrapError("Could not find OpenClaw CLI in PATH")


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise BootstrapError(
            f"Command failed ({' '.join(args)}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def parse_json_output(text: str | None) -> Any:
    if text is None:
        raise BootstrapError("Expected JSON output but command returned no stdout")
    text = text.strip()
    if not text:
        raise BootstrapError("Expected JSON output but command returned empty stdout")
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
        raise BootstrapError(f"Could not parse JSON output:\n{text}")


def openclaw_json(*args: str) -> Any:
    result = run_command([openclaw_binary(), *args])
    return parse_json_output(result.stdout)


def gateway_call_json(method: str, params: dict[str, Any] | None = None) -> Any:
    params_json = json.dumps(params or {}, separators=(",", ":"))
    try:
        return openclaw_json("gateway", "call", method, "--params", params_json)
    except BootstrapError as exc:
        raise GatewayUnavailable(str(exc)) from exc


def wait_for_gateway_config(timeout_seconds: int = 60, sleep_seconds: float = 2.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            result = gateway_call_json("config.get", {})
            if isinstance(result, dict):
                return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(sleep_seconds)
    raise GatewayUnavailable(f"Gateway did not become ready after restart: {last_error}")


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_template(text: str, values: dict[str, str]) -> str:
    rendered = text
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def summarize_standard_seed(workspace: Path) -> str:
    present = [name for name in STANDARD_WORKSPACE_FILES if (workspace / name).exists()]
    missing = [name for name in STANDARD_WORKSPACE_FILES if not (workspace / name).exists()]
    if present and not missing:
        return "complete"
    if present and missing:
        return f"partial (present: {', '.join(present)}; missing: {', '.join(missing)})"
    return "missing"


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


# ---------- OpenClaw state helpers ----------


def get_agents() -> list[dict[str, Any]]:
    agents = openclaw_json("agents", "list", "--json")
    if not isinstance(agents, list):
        raise BootstrapError("Unexpected response for openclaw agents list --json")
    return agents


def get_bindings() -> list[dict[str, Any]]:
    bindings = openclaw_json("agents", "bindings", "--json")
    if not isinstance(bindings, list):
        raise BootstrapError("Unexpected response for openclaw agents bindings --json")
    return bindings


def get_config_state() -> dict[str, Any]:
    config_state = gateway_call_json("config.get", {})
    if not isinstance(config_state, dict):
        raise GatewayUnavailable("Unexpected response for gateway config.get")
    return config_state


def find_agent(agents: list[dict[str, Any]], agent_id: str) -> dict[str, Any] | None:
    for agent in agents:
        if agent.get("id") == agent_id:
            return agent
    return None


def build_route_binding(
    agent_id: str,
    guild_id: str,
    channel_id: str,
    account_id: str | None,
) -> dict[str, Any]:
    match: dict[str, Any] = {
        "channel": "discord",
        "guildId": guild_id,
        "peer": {"kind": "channel", "id": channel_id},
    }
    if account_id:
        match["accountId"] = account_id
    return {
        "type": "route",
        "agentId": agent_id,
        "match": match,
    }


def find_binding_conflict(
    bindings: list[dict[str, Any]],
    channel_id: str,
    guild_id: str,
    agent_id: str,
) -> dict[str, Any] | None:
    for binding in bindings:
        match = binding.get("match") or {}
        peer = match.get("peer") or {}
        if (
            match.get("channel") == "discord"
            and match.get("guildId") == guild_id
            and peer.get("kind") == "channel"
            and peer.get("id") == channel_id
            and binding.get("agentId") != agent_id
        ):
            return binding
    return None


def bindings_with_route(existing_bindings: list[dict[str, Any]], new_binding: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    merged: list[dict[str, Any]] = []
    desired_key = stable_json(new_binding)
    seen: set[str] = set()
    changed = False

    for binding in existing_bindings:
        key = stable_json(binding)
        if key in seen:
            changed = True
            continue
        seen.add(key)
        merged.append(binding)

    if desired_key not in seen:
        merged.append(new_binding)
        changed = True
    return merged, changed


def build_discord_prepare_patch(
    agent_id: str,
    guild_id: str,
    channel_id: str,
    account_id: str | None,
    require_mention: bool,
) -> dict[str, Any]:
    return {
        "bindings": [
            build_route_binding(agent_id, guild_id, channel_id, account_id),
        ],
        "channels": {
            "discord": {
                "groupPolicy": "allowlist",
                "guilds": {
                    guild_id: {
                        "channels": {
                            channel_id: {
                                "allow": True,
                                "requireMention": require_mention,
                            }
                        }
                    }
                },
            }
        },
    }


def build_discord_apply_patch(
    current_config: dict[str, Any],
    agent_id: str,
    guild_id: str,
    channel_id: str,
    account_id: str | None,
    require_mention: bool,
) -> tuple[dict[str, Any], bool, dict[str, Any]]:
    desired_binding = build_route_binding(agent_id, guild_id, channel_id, account_id)

    existing_bindings = current_config.get("bindings") or []
    if not isinstance(existing_bindings, list):
        existing_bindings = []
    merged_bindings, bindings_changed = bindings_with_route(existing_bindings, desired_binding)

    discord_cfg = ((current_config.get("channels") or {}).get("discord") or {})
    guilds_cfg = discord_cfg.get("guilds") or {}
    guild_cfg = guilds_cfg.get(guild_id) or {}
    channels_cfg = guild_cfg.get("channels") or {}
    channel_cfg = channels_cfg.get(channel_id) or {}

    channel_changed = (
        channel_cfg.get("allow") is not True
        or channel_cfg.get("requireMention") is not require_mention
        or discord_cfg.get("groupPolicy") != "allowlist"
    )

    patch: dict[str, Any] = {}
    if bindings_changed:
        patch["bindings"] = merged_bindings
    if channel_changed:
        patch["channels"] = {
            "discord": {
                "groupPolicy": "allowlist",
                "guilds": {
                    guild_id: {
                        "channels": {
                            channel_id: {
                                "allow": True,
                                "requireMention": require_mention,
                            }
                        }
                    }
                },
            }
        }

    desired_summary = {
        "binding": desired_binding,
        "channel": {
            "guildId": guild_id,
            "channelId": channel_id,
            "allow": True,
            "requireMention": require_mention,
        },
    }
    changed = bool(patch)
    return patch, changed, desired_summary


def verify_discord_applied(config_state: dict[str, Any], desired_binding: dict[str, Any], guild_id: str, channel_id: str, require_mention: bool) -> tuple[bool, list[str]]:
    errors: list[str] = []
    config = config_state.get("config")
    if not isinstance(config, dict):
        return False, ["config.get returned no usable config object after patch"]

    bindings = config.get("bindings") or []
    desired_key = stable_json(desired_binding)
    if stable_json(desired_binding) not in {stable_json(item) for item in bindings if isinstance(item, dict)}:
        errors.append("route binding missing after apply")

    discord_cfg = ((config.get("channels") or {}).get("discord") or {})
    guild_cfg = ((discord_cfg.get("guilds") or {}).get(guild_id) or {})
    channel_cfg = ((guild_cfg.get("channels") or {}).get(channel_id) or {})
    if channel_cfg.get("allow") is not True:
        errors.append("channel allowlist entry missing or allow != true after apply")
    if channel_cfg.get("requireMention") is not require_mention:
        errors.append("channel requireMention does not match requested value after apply")
    if discord_cfg.get("groupPolicy") != "allowlist":
        errors.append("discord groupPolicy is not allowlist after apply")

    return len(errors) == 0, errors


# ---------- reporting helpers ----------


def summarize_outcome(checks: list[Check]) -> tuple[str, str, str]:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL", "blocked", "fail"
    if any(check.status == "WARN" for check in checks):
        return "WARN", "ready-with-warnings", "warn"
    return "PASS", "ready", "pass"


def format_text_report(report: dict[str, Any]) -> str:
    lines = [
        f"Overall: {report['overall']}",
        f"Agent: {report['agentId']}",
        f"Workspace: {report['workspace']}",
        f"Discord: {report['discordStatus']}",
        "Checks:",
    ]
    for check in report["checks"]:
        lines.append(f"- {check['status']}: {check['message']}")
    if report.get("next"):
        lines.append("Next:")
        for item in report["next"]:
            lines.append(f"- {item}")
    if report.get("discordPatch") is not None:
        lines.append("Discord patch:")
        lines.append(json.dumps(report["discordPatch"], indent=2))
    return "\n".join(lines)


def write_continuity_files(
    workspace: Path,
    replacements: dict[str, str],
) -> tuple[tuple[bool, bool], tuple[bool, bool]]:
    def write_or_preserve(path: Path, content: str) -> tuple[bool, bool]:
        if path.exists():
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError:
                existing = ""
            return False, len(existing.strip()) == 0
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True, False

    project_state_path = workspace / "PROJECT_STATE.md"
    session_start_path = workspace / "SESSION_START.txt"
    project_state_content = render_template(load_text(PROJECT_STATE_TEMPLATE), replacements)
    session_start_content = render_template(load_text(SESSION_START_TEMPLATE), replacements)
    return (
        write_or_preserve(project_state_path, project_state_content),
        write_or_preserve(session_start_path, session_start_content),
    )


# ---------- main workflow ----------


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a practical v2 OpenClaw project agent")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--agent-id")
    parser.add_argument("--workspace-path")
    parser.add_argument("--model")
    parser.add_argument("--discord-guild-id")
    parser.add_argument("--discord-channel-id")
    parser.add_argument("--discord-account-id", default="default")
    parser.add_argument("--discord-mode", choices=["none", "prepare", "apply"], default=None)
    parser.add_argument("--require-mention", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Required for discord apply mode because it writes config and restarts the gateway")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        tracker = FailureTracker()
        checks: list[Check] = []
        next_actions: list[str] = []
        project_name = args.project_name.strip()
        purpose = args.purpose.strip()
        agent_id = args.agent_id.strip() if args.agent_id else normalize_agent_id(project_name)
        workspace = Path(args.workspace_path).expanduser() if args.workspace_path else default_workspace_for(agent_id)
        workspace = workspace.resolve(strict=False)

        discord_requested = bool(args.discord_guild_id or args.discord_channel_id or args.discord_mode)
        discord_mode = args.discord_mode or ("prepare" if discord_requested else "none")
        discord_status = "not requested"
        discord_patch: dict[str, Any] | None = None
        config_hash_before: str | None = None
        config_hash_after: str | None = None

        agents = get_agents()
        existing_agent = find_agent(agents, agent_id)
        if existing_agent:
            configured_workspace = existing_agent.get("workspace") or ""
            if normalize_path(configured_workspace) != normalize_path(workspace):
                tracker.add(checks, "FAIL", f"agent exists with different workspace: {configured_workspace}")
            else:
                tracker.add(checks, "PASS", "agent already exists and workspace matches expected path")
        else:
            cmd = [
                openclaw_binary(),
                "agents",
                "add",
                agent_id,
                "--workspace",
                str(workspace),
                "--non-interactive",
                "--json",
            ]
            if args.model:
                cmd.extend(["--model", args.model])
            run_command(cmd)
            tracker.add(checks, "PASS", "agent created with openclaw agents add")
            agents = get_agents()

        verified_agent = find_agent(agents, agent_id)
        if verified_agent:
            tracker.add(checks, "PASS", "agent exists in openclaw agents list --json")
            configured_workspace = verified_agent.get("workspace") or ""
            if normalize_path(configured_workspace) == normalize_path(workspace):
                tracker.add(checks, "PASS", "agent workspace path matches expected path")
            else:
                tracker.add(checks, "FAIL", f"agent workspace path mismatch: {configured_workspace}")
        else:
            tracker.add(checks, "FAIL", "agent missing from openclaw agents list --json")

        if workspace.exists() and workspace.is_dir():
            tracker.add(checks, "PASS", "workspace directory exists on disk")
        else:
            tracker.add(checks, "FAIL", "workspace directory does not exist on disk")

        standard_seed_status = summarize_standard_seed(workspace)
        if standard_seed_status == "complete":
            tracker.add(checks, "PASS", "standard OpenClaw workspace files are present")
        elif standard_seed_status.startswith("partial"):
            tracker.add(checks, "WARN", f"standard OpenClaw workspace baseline is partial: {standard_seed_status}")
        else:
            tracker.add(checks, "WARN", "standard OpenClaw workspace baseline is missing")

        desired_binding = None
        if discord_mode in {"prepare", "apply"}:
            if not args.discord_guild_id or not args.discord_channel_id:
                tracker.add(checks, "FAIL", f"discord {discord_mode} mode requires both discordGuildId and discordChannelId")
                discord_status = "failed"
            else:
                bindings = get_bindings()
                conflict = find_binding_conflict(bindings, args.discord_channel_id, args.discord_guild_id, agent_id)
                desired_binding = build_route_binding(
                    agent_id,
                    args.discord_guild_id,
                    args.discord_channel_id,
                    args.discord_account_id,
                )
                if conflict:
                    owner = conflict.get("agentId", "unknown")
                    tracker.add(checks, "FAIL", f"discord room already bound to another agent: {owner}")
                    discord_status = "failed"
                    next_actions.append("Choose a different Discord room or remove the existing route before applying this one.")
                elif discord_mode == "prepare":
                    discord_patch = build_discord_prepare_patch(
                        agent_id,
                        args.discord_guild_id,
                        args.discord_channel_id,
                        args.discord_account_id,
                        args.require_mention,
                    )
                    tracker.add(checks, "PASS", "discord prepare plan is conflict-free")
                    discord_status = "prepared"
                    next_actions.append("Apply the generated Discord patch with --discord-mode apply --yes when you want routing to go live.")
                else:
                    if not args.yes:
                        tracker.add(checks, "FAIL", "discord apply mode requires --yes because it patches config and restarts the gateway")
                        discord_status = "failed"
                    else:
                        config_before = get_config_state()
                        config_hash_before = config_before.get("hash")
                        config_obj = config_before.get("config")
                        if not isinstance(config_obj, dict):
                            raise GatewayUnavailable("config.get returned no usable config object")
                        patch, changed, desired_summary = build_discord_apply_patch(
                            config_obj,
                            agent_id,
                            args.discord_guild_id,
                            args.discord_channel_id,
                            args.discord_account_id,
                            args.require_mention,
                        )
                        discord_patch = patch or build_discord_prepare_patch(
                            agent_id,
                            args.discord_guild_id,
                            args.discord_channel_id,
                            args.discord_account_id,
                            args.require_mention,
                        )
                        if not changed:
                            tracker.add(checks, "PASS", "discord config already matched the requested binding and allowlist state")
                            discord_status = "applied"
                        else:
                            if not config_hash_before:
                                raise GatewayUnavailable("config.get did not return a base hash for config.patch")
                            note = (
                                f"Add Discord room binding for channel '{args.discord_channel_id}' "
                                f"to agent '{agent_id}' via bootstrap_project.py"
                            )
                            patch_result = gateway_call_json(
                                "config.patch",
                                {
                                    "raw": json.dumps(patch, separators=(",", ":")),
                                    "baseHash": config_hash_before,
                                    "note": note,
                                    "restartDelayMs": 1000,
                                },
                            )
                            tracker.add(checks, "PASS", "discord config.patch applied; waiting for gateway restart")
                            config_after = wait_for_gateway_config(timeout_seconds=60, sleep_seconds=2.0)
                            config_hash_after = config_after.get("hash")
                            ok, errors = verify_discord_applied(
                                config_after,
                                desired_binding,
                                args.discord_guild_id,
                                args.discord_channel_id,
                                args.require_mention,
                            )
                            if ok:
                                tracker.add(checks, "PASS", "discord apply verification passed after restart")
                                discord_status = "applied"
                            else:
                                for error in errors:
                                    tracker.add(checks, "FAIL", error)
                                discord_status = "failed"
                                next_actions.append("Inspect the live config and rerun verification before using the room.")
        else:
            discord_status = "not requested"

        overall, bootstrap_status, validation_result = summarize_outcome(checks)
        created_at = now_iso()
        last_verified = created_at
        replacements = {
            "PROJECT_NAME": project_name,
            "PURPOSE": purpose,
            "AGENT_ID": agent_id,
            "WORKSPACE_PATH": str(workspace),
            "BOOTSTRAP_STATUS": bootstrap_status,
            "VALIDATION_RESULT": validation_result,
            "CREATED_AT_OR_DATE": created_at,
            "LAST_VERIFIED_OR_PENDING": last_verified,
            "STANDARD_SEED_STATUS": standard_seed_status,
            "CURRENT_BLOCKER_OR_NONE": tracker.current_blocker,
            "DISCORD_GUILD_ID_OR_NA": args.discord_guild_id or "n/a",
            "DISCORD_CHANNEL_ID_OR_NA": args.discord_channel_id or "n/a",
            "DISCORD_MODE_OR_NA": discord_mode if discord_mode != "none" else "n/a",
            "DISCORD_STATUS_OR_NA": discord_status if discord_mode != "none" else "n/a",
            "NEXT_ACTION_1_OR_NONE": next_actions[0] if len(next_actions) >= 1 else "none",
            "NEXT_ACTION_2_OR_NONE": next_actions[1] if len(next_actions) >= 2 else "none",
        }

        (created_project_state, warn_project_state), (created_session_start, warn_session_start) = write_continuity_files(
            workspace,
            replacements,
        )

        project_state_path = workspace / "PROJECT_STATE.md"
        session_start_path = workspace / "SESSION_START.txt"
        if project_state_path.exists():
            tracker.add(checks, "PASS", "PROJECT_STATE.md exists")
        else:
            tracker.add(checks, "FAIL", "PROJECT_STATE.md is missing")
        if session_start_path.exists():
            tracker.add(checks, "PASS", "SESSION_START.txt exists")
        else:
            tracker.add(checks, "FAIL", "SESSION_START.txt is missing")
        if warn_project_state:
            tracker.add(checks, "WARN", "existing PROJECT_STATE.md is empty; preserved without overwrite")
        if warn_session_start:
            tracker.add(checks, "WARN", "existing SESSION_START.txt is empty; preserved without overwrite")
        if created_project_state:
            tracker.add(checks, "PASS", "PROJECT_STATE.md created from template")
        if created_session_start:
            tracker.add(checks, "PASS", "SESSION_START.txt created from template")

        overall, bootstrap_status, validation_result = summarize_outcome(checks)
        if created_project_state or created_session_start:
            final_replacements = dict(replacements)
            final_replacements["BOOTSTRAP_STATUS"] = bootstrap_status
            final_replacements["VALIDATION_RESULT"] = validation_result
            final_replacements["CURRENT_BLOCKER_OR_NONE"] = tracker.current_blocker
            if created_project_state:
                project_state_path.write_text(
                    render_template(load_text(PROJECT_STATE_TEMPLATE), final_replacements),
                    encoding="utf-8",
                )
            if created_session_start:
                session_start_path.write_text(
                    render_template(load_text(SESSION_START_TEMPLATE), final_replacements),
                    encoding="utf-8",
                )

        report = {
            "overall": overall,
            "agentId": agent_id,
            "workspace": str(workspace),
            "discordStatus": discord_status,
            "checks": [{"status": c.status, "message": c.message} for c in checks],
            "next": next_actions,
            "discordPatch": discord_patch,
            "metadata": {
                "projectName": project_name,
                "purpose": purpose,
                "discordMode": discord_mode,
                "bootstrapStatus": bootstrap_status,
                "validationResult": validation_result,
                "standardSeedStatus": standard_seed_status,
                "currentBlocker": tracker.current_blocker,
                "configHashBefore": config_hash_before,
                "configHashAfter": config_hash_after,
            },
        }

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(format_text_report(report))
        return 0 if overall != "FAIL" else 1
    except BootstrapError as exc:
        report = {
            "overall": "FAIL",
            "agentId": args.agent_id or "unknown",
            "workspace": args.workspace_path or "unknown",
            "discordStatus": "failed" if args.discord_mode else "not requested",
            "checks": [{"status": "FAIL", "message": str(exc)}],
            "next": [],
            "discordPatch": None,
        }
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(format_text_report(report))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
