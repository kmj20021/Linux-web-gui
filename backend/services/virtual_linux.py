"""Deterministic, side-effect-free Linux state simulator."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from services.command_parser import ParsedCommand, parse_command


@dataclass(frozen=True)
class ExecutionResult:
    result_code: str
    output: str
    state_before: dict[str, Any]
    state_after: dict[str, Any]


def execute_command(state: dict[str, Any], command_text: str) -> ExecutionResult:
    """Apply a supported command to copied state; never execute host commands."""
    before = deepcopy(state)
    after = deepcopy(state)
    parsed = parse_command(command_text)
    if parsed.command is None:
        return ExecutionResult(parsed.result_code, parsed.result_code, before, after)

    output = _apply(after, parsed.command)
    if output is None:
        return ExecutionResult("unsupported_syntax", "unsupported_syntax", before, before)
    return ExecutionResult("success", output, before, after)


def _apply(state: dict[str, Any], command: ParsedCommand) -> str | None:
    name, action, args = command.name, command.action, command.arguments
    if name == "systemctl" and action == "status" and not args:
        services = state.get("services", {})
        if not services:
            return "(no simulated services registered)"
        return "\n".join(
            f"{service_name}: {'active' if service.get('active') else 'inactive'}; "
            f"{'enabled' if service.get('enabled') else 'disabled'}"
            for service_name, service in sorted(services.items())
        )
    if name == "systemctl" and len(args) == 1:
        service = state.get("services", {}).get(args[0])
        if service is None:
            return None
        if action == "status":
            status = "active" if service.get("active") else "inactive"
            # Keep one canonical output for an identical state and command.
            # Enabled is reported when true; false is represented by its
            # absence so basic status remains "active"/"inactive".
            if service.get("enabled"):
                status += "; enabled"
            return status
        if action in {"start", "restart", "stop"}:
            service["active"] = action != "stop"
            _refresh_remote_access(state)
            return {"start": "started", "restart": "restarted", "stop": "stopped"}[action]
        service["enabled"] = action == "enable"
        return "enabled" if action == "enable" else "disabled"

    if name == "curl" and args == ("http://localhost",):
        nginx = state.get("services", {}).get("nginx", {})
        if nginx.get("active"):
            return "reachable"
        return None
    if name == "curl" and args == ("-I", "http://localhost"):
        nginx = state.get("services", {}).get("nginx", {})
        if nginx.get("active"):
            return ("HTTP/1.1 200 OK\nServer: nginx (simulation)\n"
                    "Content-Type: text/html\nContent-Length: 0\n\n")
        return "curl: (7) Failed to connect to localhost port 80: Connection refused (simulation)"
    if name in {"useradd", "userdel", "passwd"} and len(args) == 1:
        users = state.setdefault("users", {})
        user = args[0]
        if name == "useradd":
            users[user] = {"exists": True, "password_configured": False}
            return "user created"
        if name == "userdel":
            users.pop(user, None)
            return "user deleted"
        if user not in users:
            return None
        users[user]["password_configured"] = True
        return "password marked configured"
    if name == "chown" and len(args) == 2 and ":" in args[0]:
        file_state = state.get("files", {}).get(args[1])
        owner, group = args[0].split(":", 1)
        if file_state is None or owner not in state.get("users", {}) or not owner or not group:
            return None
        file_state.update(owner=owner, group=group)
        return "owner changed"
    if name == "chmod" and len(args) == 2 and args[0].isdigit():
        file_state = state.get("files", {}).get(args[1])
        if file_state is None:
            return None
        file_state["mode"] = args[0]
        return "mode changed"
    if name == "ls" and not args:
        entries: set[str] = set()
        for path in state.get("files", {}):
            if isinstance(path, str) and path.startswith("/"):
                component = path.lstrip("/").split("/", 1)[0]
                if component:
                    entries.add(component)
        for pseudo in ("services", "packages", "users"):
            if state.get(pseudo):
                entries.add(pseudo)
        return "\n".join(sorted(entries)) if entries else "(empty simulated directory)"
    if name == "ls" and len(args) == 1:
        file_state = state.get("files", {}).get(args[0])
        return f'{file_state["owner"]} {file_state["group"]} {file_state["mode"]}' if file_state else None
    if name == "cat" and len(args) == 1 and args[0] in state.get("files", {}):
        return "read allowed by simulated policy"
    if name == "ss" and not args:
        ports = state.get("listening_ports", [])
        if 22 in ports:
            state.setdefault("diagnosis", {})["ssh_listening"] = True
            return "port 22 listening"
        return "no listening ports"
    if name == "ufw" and action == "status" and not args:
        rule = state.get("firewall", {}).get("22/tcp")
        if rule is None:
            return None
        diagnosis = state.setdefault("diagnosis", {})
        diagnosis["firewall_blocks_22"] = rule == "deny"
        return f"22/tcp {rule}"
    if name == "ufw" and action in {"allow", "deny"} and len(args) == 1 and args[0] in {"22", "22/tcp"}:
        state.setdefault("firewall", {})["22/tcp"] = action
        diagnosis = state.get("diagnosis")
        if diagnosis is not None:
            diagnosis["firewall_blocks_22"] = action == "deny"
        _refresh_remote_access(state)
        return "rule updated; remote access available" if state.get("remote_access") == "available" else "rule updated"
    if name == "ping" and args == ("training-server",):
        diagnosis = state.setdefault("diagnosis", {})
        if diagnosis.get("ssh_listening") and diagnosis.get("firewall_blocks_22"):
            diagnosis["cause"] = "firewall_rule"
        return "host reachable; SSH still blocked"
    if name == "apt" and action in {"install", "remove"} and len(args) == 1:
        state.setdefault("packages", {})[args[0]] = "installed" if action == "install" else "removed"
        return "installed" if action == "install" else "removed"
    return None


def _refresh_remote_access(state: dict[str, Any]) -> None:
    if "remote_access" not in state:
        return
    ssh_active = state.get("services", {}).get("ssh", {}).get("active", False)
    allowed = state.get("firewall", {}).get("22/tcp") == "allow"
    state["remote_access"] = "available" if ssh_active and allowed else "blocked"
