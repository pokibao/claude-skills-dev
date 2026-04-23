#!/usr/bin/env python3
"""
Chain Manager — 多步骤工作流追踪

命令:
  new     --name "名称" [--steps "a,b,c" | --template tpl_id]
  status  (list active chains)
  advance --id chain_id [--note "进度说明"]
  block   --id chain_id --reason "阻塞原因"
  resume  --id chain_id
  done    --id chain_id
  list    (list all including archived)

数据存储: ~/.claude/skills/pulse/data/chains/chain_*.json
归档:     ~/.claude/skills/pulse/data/chains/archive/chain_*.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

CHAINS_DIR = Path.home() / ".claude" / "skills" / "pulse" / "data" / "chains"
ARCHIVE_DIR = CHAINS_DIR / "archive"
TEMPLATES_DIR = Path.home() / ".claude" / "skills" / "chain" / "templates"

# Built-in templates
BUILTIN_TEMPLATES = {
    "xhs_publish": {
        "steps": ["选图", "写文案", "品牌审核", "发布", "验证"],
        "description": "小红书批量发布流程",
    },
    "lookbook_gen": {
        "steps": ["选款", "配模特", "生图", "验图", "排版"],
        "description": "Lookbook 生成流程",
    },
    "ig_publish": {
        "steps": ["选图", "写IG文案", "发Story", "发Post", "验证"],
        "description": "Instagram 发布流程",
    },
    "trend_research": {
        "steps": ["抓秀场", "分析趋势", "匹配DNA", "出报告"],
        "description": "时尚趋势调研流程",
    },
}


def make_chain_id(name: str) -> str:
    """Generate a chain ID from name + timestamp."""
    # Sanitize name: keep alphanumeric + chinese + underscore
    slug = re.sub(r'[^\w\u4e00-\u9fff]', '_', name).strip('_')[:20]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{ts}"


def find_chain_file(chain_id_prefix: str) -> Path | None:
    """Find a chain file by ID prefix match."""
    if not CHAINS_DIR.exists():
        return None
    for f in sorted(CHAINS_DIR.glob("chain_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            cid = data.get("chain_id", "")
            if cid == chain_id_prefix or cid.startswith(chain_id_prefix):
                return f
        except Exception:
            continue
    return None


def load_chain(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_chain(data: dict) -> Path:
    CHAINS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"chain_{data['chain_id']}.json"
    path = CHAINS_DIR / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def cmd_new(args):
    """Create a new chain."""
    name = args.name
    steps = None
    template_id = None

    if args.template:
        template_id = args.template
        if template_id in BUILTIN_TEMPLATES:
            steps = BUILTIN_TEMPLATES[template_id]["steps"]
        else:
            # Try loading from templates dir
            tpl_file = TEMPLATES_DIR / f"{template_id}.json"
            if tpl_file.exists():
                tpl = json.loads(tpl_file.read_text(encoding="utf-8"))
                steps = tpl.get("steps", [])
            else:
                print(f"Error: Template '{template_id}' not found.")
                print(f"Available: {', '.join(BUILTIN_TEMPLATES.keys())}")
                sys.exit(1)
    elif args.steps:
        steps = [s.strip() for s in args.steps.split(",") if s.strip()]

    if not steps:
        print("Error: Must provide --steps or --template")
        sys.exit(1)

    chain_id = make_chain_id(name)
    now = datetime.now().isoformat()

    chain = {
        "chain_id": chain_id,
        "name": name,
        "template": template_id,
        "steps": steps,
        "current_step": 0,
        "status": "in_progress",
        "blocker": None,
        "created_at": now,
        "updated_at": now,
        "history": [],
    }

    path = save_chain(chain)
    print(f"Chain created: {chain_id}")
    print(f"  Name: {name}")
    print(f"  Steps: {' -> '.join(steps)}")
    print(f"  File: {path}")
    print(f"  Current: Step 1/{len(steps)} ({steps[0]})")


def cmd_status(_args):
    """Show all active chains."""
    if not CHAINS_DIR.exists():
        print("No chains found.")
        return

    chains = []
    for f in sorted(CHAINS_DIR.glob("chain_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") in ("in_progress", "blocked"):
                chains.append(data)
        except Exception:
            continue

    if not chains:
        print("No active chains.")
        return

    print(f"## Active Chains ({len(chains)})\n")
    for i, c in enumerate(chains, 1):
        steps = c.get("steps", [])
        current = c.get("current_step", 0)
        total = len(steps)

        # Build step progress bar
        step_parts = []
        for j, step_name in enumerate(steps):
            if j < current:
                step_parts.append(f"{step_name} \u2713")
            elif j == current:
                step_parts.append(f"{step_name} \u25cf")
            else:
                step_parts.append(f"{step_name} \u25cb")

        status_str = ""
        if c.get("status") == "blocked":
            status_str = f" BLOCKED: {c.get('blocker', 'unknown')}"

        current_name = steps[current] if current < total else "done"
        print(f"{i}. [{c['name']}] Step {current + 1}/{total}: {current_name}{status_str}")
        print(f"   ID: {c['chain_id']}")
        print(f"   Progress: {' -> '.join(step_parts)}")
        print(f"   Updated: {c.get('updated_at', '')[:16]}")
        print()


def cmd_advance(args):
    """Advance chain to next step."""
    chain_file = find_chain_file(args.id)
    if not chain_file:
        print(f"Error: Chain '{args.id}' not found.")
        sys.exit(1)

    chain = load_chain(chain_file)
    steps = chain.get("steps", [])
    current = chain.get("current_step", 0)

    if current >= len(steps) - 1:
        print(f"Chain '{chain['name']}' is already at the last step.")
        print("Use `/chain done` to complete it.")
        return

    # Record history
    now = datetime.now().isoformat()
    chain["history"].append({
        "step": current,
        "step_name": steps[current],
        "action": "advance",
        "note": args.note or "",
        "at": now,
    })

    chain["current_step"] = current + 1
    chain["updated_at"] = now
    chain["status"] = "in_progress"
    chain["blocker"] = None

    save_chain(chain)
    # Remove old file if ID changed (shouldn't, but safety)
    if chain_file != CHAINS_DIR / f"chain_{chain['chain_id']}.json":
        chain_file.unlink(missing_ok=True)

    next_name = steps[current + 1]
    print(f"Advanced: {chain['name']}")
    print(f"  Completed: {steps[current]}")
    print(f"  Now at: Step {current + 2}/{len(steps)} ({next_name})")
    if args.note:
        print(f"  Note: {args.note}")


def cmd_block(args):
    """Mark chain as blocked."""
    chain_file = find_chain_file(args.id)
    if not chain_file:
        print(f"Error: Chain '{args.id}' not found.")
        sys.exit(1)

    chain = load_chain(chain_file)
    now = datetime.now().isoformat()

    chain["status"] = "blocked"
    chain["blocker"] = args.reason
    chain["updated_at"] = now
    chain["history"].append({
        "step": chain.get("current_step", 0),
        "step_name": chain.get("steps", [])[chain.get("current_step", 0)]
            if chain.get("current_step", 0) < len(chain.get("steps", []))
            else "unknown",
        "action": "block",
        "note": args.reason,
        "at": now,
    })

    save_chain(chain)
    print(f"Blocked: {chain['name']}")
    print(f"  Reason: {args.reason}")
    print(f"  Step: {chain.get('current_step', 0) + 1}/{len(chain.get('steps', []))}")


def cmd_resume(args):
    """Show chain state for resumption."""
    chain_file = find_chain_file(args.id)
    if not chain_file:
        print(f"Error: Chain '{args.id}' not found.")
        sys.exit(1)

    chain = load_chain(chain_file)
    steps = chain.get("steps", [])
    current = chain.get("current_step", 0)
    current_name = steps[current] if current < len(steps) else "done"

    # If blocked, unblock
    if chain.get("status") == "blocked":
        now = datetime.now().isoformat()
        chain["status"] = "in_progress"
        old_blocker = chain.get("blocker", "")
        chain["blocker"] = None
        chain["updated_at"] = now
        chain["history"].append({
            "step": current,
            "step_name": current_name,
            "action": "resume",
            "note": f"Resumed from block: {old_blocker}",
            "at": now,
        })
        save_chain(chain)
        print(f"Resumed (was blocked: {old_blocker})")
    else:
        print(f"Resuming chain (was {chain.get('status')})")

    print(f"\n## Chain: {chain['name']}")
    print(f"Current: Step {current + 1}/{len(steps)} -- {current_name}")
    print(f"Template: {chain.get('template', 'custom')}")
    print()

    # Show history
    if chain.get("history"):
        print("### History")
        for h in chain["history"]:
            print(f"  [{h.get('at', '')[:16]}] {h.get('action', '')}: {h.get('step_name', '')} -- {h.get('note', '')}")
        print()

    # Show remaining steps
    print("### Remaining Steps")
    for i in range(current, len(steps)):
        marker = ">>>" if i == current else "   "
        print(f"  {marker} {i + 1}. {steps[i]}")


def cmd_done(args):
    """Complete and archive a chain."""
    chain_file = find_chain_file(args.id)
    if not chain_file:
        print(f"Error: Chain '{args.id}' not found.")
        sys.exit(1)

    chain = load_chain(chain_file)
    now = datetime.now().isoformat()

    chain["status"] = "completed"
    chain["updated_at"] = now
    chain["completed_at"] = now
    chain["history"].append({
        "step": chain.get("current_step", 0),
        "step_name": chain.get("steps", [])[chain.get("current_step", 0)]
            if chain.get("current_step", 0) < len(chain.get("steps", []))
            else "final",
        "action": "done",
        "note": "Chain completed",
        "at": now,
    })

    # Archive
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARCHIVE_DIR / chain_file.name
    archive_path.write_text(json.dumps(chain, ensure_ascii=False, indent=2), encoding="utf-8")

    # Remove from active
    chain_file.unlink(missing_ok=True)

    print(f"Completed: {chain['name']}")
    print(f"  Steps: {len(chain.get('steps', []))}")
    print(f"  Duration: {chain.get('created_at', '')[:10]} -> {now[:10]}")
    print(f"  Archived to: {archive_path}")


def cmd_list(_args):
    """List all chains including archived."""
    print("## All Chains\n")

    # Active
    active = []
    if CHAINS_DIR.exists():
        for f in sorted(CHAINS_DIR.glob("chain_*.json")):
            try:
                active.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue

    if active:
        print(f"### Active ({len(active)})")
        for c in active:
            steps = c.get("steps", [])
            current = c.get("current_step", 0)
            name = steps[current] if current < len(steps) else "done"
            status = c.get("status", "")
            print(f"  - [{c['name']}] {current + 1}/{len(steps)} ({name}) [{status}] id={c['chain_id']}")
        print()

    # Archived
    archived = []
    if ARCHIVE_DIR.exists():
        for f in sorted(ARCHIVE_DIR.glob("chain_*.json")):
            try:
                archived.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue

    if archived:
        print(f"### Archived ({len(archived)})")
        for c in archived:
            print(f"  - [{c['name']}] completed {c.get('completed_at', '')[:10]} ({len(c.get('steps', []))} steps)")
        print()

    if not active and not archived:
        print("No chains found.")


def main():
    parser = argparse.ArgumentParser(description="Chain Manager - Multi-step workflow tracker")
    subparsers = parser.add_subparsers(dest="command")

    # new
    p_new = subparsers.add_parser("new", help="Create new chain")
    p_new.add_argument("--name", required=True, help="Chain name")
    p_new.add_argument("--steps", help="Comma-separated steps")
    p_new.add_argument("--template", help="Template ID")

    # status
    subparsers.add_parser("status", help="Show active chains")

    # advance
    p_adv = subparsers.add_parser("advance", help="Advance to next step")
    p_adv.add_argument("--id", required=True, help="Chain ID (prefix match)")
    p_adv.add_argument("--note", default="", help="Progress note")

    # block
    p_block = subparsers.add_parser("block", help="Mark as blocked")
    p_block.add_argument("--id", required=True, help="Chain ID")
    p_block.add_argument("--reason", required=True, help="Block reason")

    # resume
    p_resume = subparsers.add_parser("resume", help="Resume from block")
    p_resume.add_argument("--id", required=True, help="Chain ID")

    # done
    p_done = subparsers.add_parser("done", help="Complete and archive")
    p_done.add_argument("--id", required=True, help="Chain ID")

    # list
    subparsers.add_parser("list", help="List all chains")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "new": cmd_new,
        "status": cmd_status,
        "advance": cmd_advance,
        "block": cmd_block,
        "resume": cmd_resume,
        "done": cmd_done,
        "list": cmd_list,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
