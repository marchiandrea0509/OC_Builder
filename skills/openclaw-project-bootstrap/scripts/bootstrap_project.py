#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
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
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise BootstrapError(
            f"Command failed ({' '.join(args)}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def parse_json_output(text: str) -> Any:
    text = text.strip()
    if not text:
        raise BootstrapError("Expected JSON output but command returned empty stdout")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        candidates = []
        for idx, ch in enumerate(text):
            if ch not in "[{":
                continue
            try:
                obj, end = decoder.raw_decode(text[idx:])
                candidates.append(obj)
            except json.JSONDecodeError:
                continue
        if candidates:
            return candidates[-1]
        raise BootstrapError(f"Could not parse JSON output:\n{text}")


def openclaw_json(*args: str) -> Any:
    result = run_command([openclaw_binary(), *args])
    return parse_json_output(result.stdout)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_template(text: str, values: dict[str, str]) -> str:
    rendered = text
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def write_if_missing(path: Path, content: str) -> tuple[bool, bool]:
    """Return (created, warn_empty_existing)."""
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError:
            existing = ""
        return False, len(existing.strip()) == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True, False


def summarize_standard_seed(workspace: Path) -> str:
    present = [name for name in STANDARD_WORKSPACE_FILES if (workspace / name).exists()]
    missing = [name for name in STANDARD_WORKSPACE_FILES if not (workspace / name).exists()]
    if present and not missing:
        return "complete"
    if present and missing:
        return f"partial (present: {', '.join(present)}; missing: {', '.join(missing)})"
    return "missing"


def find_agent(agents: list[dict[str, Any]], agent_id: str) -> dict[str, Any] | None:
    for agent in agents:
        if agent.get("id") == agent_id:
            return agent
    return None


def find_binding_conflict(bindings: list[dict[str, Any]], channel_id: str, guild_id: str, agent_id: str) -> dict[str, Any] | None:
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


def build_discord_patch(agent_id: str, guild_id: str, channel_id: str, account_id: str, require_mention: bool) -> dict[str, Any]:
    return {
        "bindings": [
            {
                "agentId": agent_id,
                "match": {
                    "channel": "discord",
                    "accountId": account_id,
                    "peer": {"kind": "channel", "id": channel_id},
                },
            }
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a practical v1 OpenClaw project agent")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--agent-id")
    parser.add_argument("--workspace-path")
    parser.add_argument("--model")
    parser.add_argument("--discord-guild-id")
    parser.add_argument("--discord-channel-id")
    parser.add_argument("--discord-account-id", default="default")
    parser.add_argument("--discord-mode", choices=["none", "prepare"], default=None)
    parser.add_argument("--require-mention", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        project_name = args.project_name.strip()
        purpose = args.purpose.strip()
        agent_id = args.agent_id.strip() if args.agent_id else normalize_agent_id(project_name)
        workspace = Path(args.workspace_path).expanduser() if args.workspace_path else default_workspace_for(agent_id)
        workspace = workspace.resolve(strict=False)

        discord_requested = bool(args.discord_guild_id or args.discord_channel_id or args.discord_mode)
        discord_mode = args.discord_mode or ("prepare" if discord_requested else "none")
        discord_status = "not requested"
        current_blocker = "none"
        next_actions: list[str] = []
        checks: list[Check] = []
        discord_patch = None

        agents = openclaw_json("agents", "list", "--json")
        if not isinstance(agents, list):
            raise BootstrapError("Unexpected response for openclaw agents list --json")

        existing_agent = find_agent(agents, agent_id)
        if existing_agent:
            configured_workspace = existing_agent.get("workspace") or ""
            if normalize_path(configured_workspace) != normalize_path(workspace):
                checks.append(Check("FAIL", f"agent exists with different workspace: {configured_workspace}"))
                current_blocker = "agent/workspace mismatch"
            else:
                checks.append(Check("PASS", "agent already exists and workspace matches expected path"))
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
            checks.append(Check("PASS", "agent created with openclaw agents add"))
            agents = openclaw_json("agents", "list", "--json")

        verified_agent = find_agent(agents, agent_id)
        if verified_agent:
            checks.append(Check("PASS", "agent exists in openclaw agents list --json"))
            configured_workspace = verified_agent.get("workspace") or ""
            if normalize_path(configured_workspace) == normalize_path(workspace):
                checks.append(Check("PASS", "agent workspace path matches expected path"))
            else:
                checks.append(Check("FAIL", f"agent workspace path mismatch: {configured_workspace}"))
                current_blocker = "agent/workspace mismatch"
        else:
            checks.append(Check("FAIL", "agent missing from openclaw agents list --json"))
            current_blocker = "agent missing from CLI registration"

        if workspace.exists() and workspace.is_dir():
            checks.append(Check("PASS", "workspace directory exists on disk"))
        else:
            checks.append(Check("FAIL", "workspace directory does not exist on disk"))
            current_blocker = "workspace directory missing"

        standard_seed_status = summarize_standard_seed(workspace)
        if standard_seed_status == "complete":
            checks.append(Check("PASS", "standard OpenClaw workspace files are present"))
        elif standard_seed_status.startswith("partial"):
            checks.append(Check("WARN", f"standard OpenClaw workspace baseline is partial: {standard_seed_status}"))
        else:
            checks.append(Check("WARN", "standard OpenClaw workspace baseline is missing"))

        if discord_mode == "prepare":
            if not args.discord_guild_id or not args.discord_channel_id:
                checks.append(Check("FAIL", "discord prepare mode requires both discordGuildId and discordChannelId"))
                discord_status = "failed"
                current_blocker = "missing Discord ids"
            else:
                bindings = openclaw_json("agents", "bindings", "--json")
                if not isinstance(bindings, list):
                    raise BootstrapError("Unexpected response for openclaw agents bindings --json")
                conflict = find_binding_conflict(bindings, args.discord_channel_id, args.discord_guild_id, agent_id)
                discord_patch = build_discord_patch(
                    agent_id,
                    args.discord_guild_id,
                    args.discord_channel_id,
                    args.discord_account_id,
                    args.require_mention,
                )
                if conflict:
                    owner = conflict.get("agentId", "unknown")
                    checks.append(Check("FAIL", f"discord room already bound to another agent: {owner}"))
                    discord_status = "failed"
                    current_blocker = f"discord room owned by {owner}"
                    next_actions.append("Choose a different Discord room or remove the existing route before applying this one.")
                else:
                    checks.append(Check("PASS", "discord prepare plan is conflict-free"))
                    discord_status = "prepared"
                    next_actions.append("Apply the generated Discord patch with gateway config.patch when you want routing to go live.")
        else:
            discord_status = "not requested"

        created_at = now_iso()
        last_verified = created_at

        non_fail_statuses = {check.status for check in checks if check.status != "FAIL"}
        if any(check.status == "FAIL" for check in checks):
            overall = "FAIL"
            bootstrap_status = "blocked"
            validation_result = "fail"
        elif any(check.status == "WARN" for check in checks):
            overall = "WARN"
            bootstrap_status = "ready-with-warnings"
            validation_result = "warn"
        else:
            overall = "PASS"
            bootstrap_status = "ready"
            validation_result = "pass"

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
            "CURRENT_BLOCKER_OR_NONE": current_blocker,
            "DISCORD_GUILD_ID_OR_NA": args.discord_guild_id or "n/a",
            "DISCORD_CHANNEL_ID_OR_NA": args.discord_channel_id or "n/a",
            "DISCORD_MODE_OR_NA": discord_mode if discord_mode != "none" else "n/a",
            "DISCORD_STATUS_OR_NA": discord_status if discord_mode != "none" else "n/a",
            "NEXT_ACTION_1_OR_NONE": next_actions[0] if len(next_actions) >= 1 else "none",
            "NEXT_ACTION_2_OR_NONE": next_actions[1] if len(next_actions) >= 2 else "none",
        }

        project_state_path = workspace / "PROJECT_STATE.md"
        session_start_path = workspace / "SESSION_START.txt"
        project_state_content = render_template(load_text(PROJECT_STATE_TEMPLATE), replacements)
        session_start_content = render_template(load_text(SESSION_START_TEMPLATE), replacements)

        created_project_state, warn_project_state = write_if_missing(project_state_path, project_state_content)
        created_session_start, warn_session_start = write_if_missing(session_start_path, session_start_content)

        if project_state_path.exists():
            checks.append(Check("PASS", "PROJECT_STATE.md exists"))
        else:
            checks.append(Check("FAIL", "PROJECT_STATE.md is missing"))
        if session_start_path.exists():
            checks.append(Check("PASS", "SESSION_START.txt exists"))
        else:
            checks.append(Check("FAIL", "SESSION_START.txt is missing"))
        if warn_project_state:
            checks.append(Check("WARN", "existing PROJECT_STATE.md is empty; preserved without overwrite"))
        if warn_session_start:
            checks.append(Check("WARN", "existing SESSION_START.txt is empty; preserved without overwrite"))
        if created_project_state:
            checks.append(Check("PASS", "PROJECT_STATE.md created from template"))
        if created_session_start:
            checks.append(Check("PASS", "SESSION_START.txt created from template"))

        if any(check.status == "FAIL" for check in checks):
            overall = "FAIL"
            bootstrap_status = "blocked"
            validation_result = "fail"
        elif any(check.status == "WARN" for check in checks):
            overall = "WARN"
            bootstrap_status = "ready-with-warnings"
            validation_result = "warn"
        else:
            overall = "PASS"
            bootstrap_status = "ready"
            validation_result = "pass"

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
                "currentBlocker": current_blocker,
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
