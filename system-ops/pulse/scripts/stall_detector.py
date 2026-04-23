#!/usr/bin/env python3
"""
Stall Detector — 扫描 MA checkpoints 和 chains 找停滞项

检测逻辑:
  - MA checkpoints: in_progress/blocked 且 >3 天无更新
  - Chains: in_progress/blocked 且 >2 天无更新

输出: markdown 格式的停滞报告

注意: MA checkpoints 需要通过 MCP 调用 search_checkpoints，
      这里只处理 chain 文件的停滞检测。
      MA 部分由 SKILL.md 指导 Claude 用 MCP 工具补充。
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

CHAINS_DIR = Path.home() / ".claude" / "skills" / "pulse" / "data" / "chains"
STALL_THRESHOLD_DAYS = 2  # chains stale after 2 days


def detect_stale_chains() -> list[dict]:
    """Find chains that haven't been updated in STALL_THRESHOLD_DAYS."""
    stale = []
    if not CHAINS_DIR.exists():
        return stale

    now = datetime.now()
    threshold = now - timedelta(days=STALL_THRESHOLD_DAYS)

    for f in sorted(CHAINS_DIR.glob("chain_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") not in ("in_progress", "blocked"):
                continue

            updated_at = data.get("updated_at", "")
            if updated_at:
                updated = datetime.fromisoformat(updated_at)
                if updated < threshold:
                    days_stale = (now - updated).days
                    stale.append({
                        "chain_id": data.get("chain_id"),
                        "name": data.get("name"),
                        "status": data.get("status"),
                        "blocker": data.get("blocker"),
                        "current_step": data.get("current_step", 0),
                        "total_steps": len(data.get("steps", [])),
                        "current_step_name": data.get("steps", [])[data.get("current_step", 0)]
                            if data.get("current_step", 0) < len(data.get("steps", []))
                            else "unknown",
                        "updated_at": updated_at,
                        "days_stale": days_stale,
                    })
        except Exception:
            continue

    return sorted(stale, key=lambda x: -x["days_stale"])


def render_stall_report(stale_chains: list[dict]) -> str:
    """Render stall detection report as markdown."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## Stall Detection -- {today}", ""]

    # Chain stalls
    if stale_chains:
        lines.append(f"### Stale Chains (no update >{STALL_THRESHOLD_DAYS}d)")
        for c in stale_chains:
            icon = "BLOCKED" if c["status"] == "blocked" else "STALE"
            lines.append(
                f"- **{c['name']}** [{icon}]: Step {c['current_step']}/{c['total_steps']} "
                f"({c['current_step_name']}), last update {c['days_stale']}d ago"
            )
            if c["blocker"]:
                lines.append(f"  Blocker: {c['blocker']}")
    else:
        lines.append("### Chains: All clear")

    lines.append("")
    lines.append("### MA Checkpoints")
    lines.append("Run `search_checkpoints(task_status=\"active\")` via Memory Anchor MCP to check stale checkpoints.")
    lines.append("")
    lines.append("### Recommendations")
    if stale_chains:
        lines.append("- Use `/chain block <id> <reason>` to document why a chain is stuck")
        lines.append("- Use `/chain done <id>` to archive completed/abandoned chains")
        lines.append("- Use `save_checkpoint(task_status=\"abandoned\")` for MA items no longer relevant")
    else:
        lines.append("- No stale chains detected. Check MA checkpoints above.")

    return "\n".join(lines)


def main():
    stale_chains = detect_stale_chains()
    print(render_stall_report(stale_chains))

    # Also output JSON for programmatic use
    if "--json" in sys.argv:
        print("\n---JSON---")
        print(json.dumps({"stale_chains": stale_chains}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
