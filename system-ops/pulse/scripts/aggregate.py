#!/usr/bin/env python3
"""
Pulse Aggregate — 聚合所有会话数据生成每日/每周 JSON

数据源:
  - pending-memories/flush_*.json (会话状态 + accomplishments)
  - skill-usage.log (skill 调用历史)
  - /tmp/.claude_skills_today (当日 skill 快照)
  - git log (今日 commits)
  - pulse/data/chains/*.json (活跃链路)

输出:
  - pulse/data/daily/YYYY-MM-DD.json
  - stdout: markdown dashboard
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PENDING_DIR = Path.home() / ".claude" / "pending-memories"
SKILL_LOG = Path.home() / ".claude" / "skill-usage.log"
SKILLS_TODAY = Path("/tmp/.claude_skills_today")
CHAINS_DIR = Path.home() / ".claude" / "skills" / "pulse" / "data" / "chains"
DAILY_DIR = Path.home() / ".claude" / "skills" / "pulse" / "data" / "daily"


def collect_sessions(date_str: str) -> list[dict]:
    """Collect session data from pending-memories for a given date."""
    sessions = []
    for f in sorted(PENDING_DIR.glob("flush_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            ts = data.get("timestamp", "")
            if ts.startswith(date_str):
                sessions.append(data)
        except Exception:
            continue
    return sessions


def collect_skills_today() -> list[str]:
    """Read today's skill usage from /tmp/.claude_skills_today."""
    skills = []
    if SKILLS_TODAY.exists():
        try:
            for line in SKILLS_TODAY.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    skills.append(line.strip())
        except Exception:
            pass
    return skills


def collect_skill_log(date_str: str) -> list[dict]:
    """Parse skill-usage.log for entries matching date."""
    entries = []
    if not SKILL_LOG.exists():
        return entries
    try:
        for line in SKILL_LOG.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0].startswith(date_str):
                entries.append({
                    "time": parts[0],
                    "user": parts[1] if len(parts) > 1 else "",
                    "skill": parts[2] if len(parts) > 2 else "",
                    "args": parts[3] if len(parts) > 3 else "",
                    "session": parts[4] if len(parts) > 4 else "",
                })
    except Exception:
        pass
    return entries


def collect_git_commits(date_str: str) -> list[dict]:
    """Get git commits from today across known project dirs."""
    commits = []
    # Try current dir and common project dirs
    dirs_to_check = [os.getcwd()]
    projects_dir = Path.home() / "projects"
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if d.is_dir() and (d / ".git").exists():
                dirs_to_check.append(str(d))

    seen_hashes = set()
    for d in dirs_to_check:
        try:
            result = subprocess.run(
                ["git", "log", f"--since={date_str}", "--format=%H|%s|%ai", "--all"],
                capture_output=True, text=True, timeout=3, cwd=d
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip() or "|" not in line:
                        continue
                    parts = line.split("|", 2)
                    h = parts[0][:8]
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        commits.append({
                            "hash": h,
                            "message": parts[1] if len(parts) > 1 else "",
                            "date": parts[2] if len(parts) > 2 else "",
                            "repo": os.path.basename(d),
                        })
        except Exception:
            continue
    return commits


def collect_active_chains() -> list[dict]:
    """Read active chain files."""
    chains = []
    if not CHAINS_DIR.exists():
        return chains
    for f in sorted(CHAINS_DIR.glob("chain_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") in ("in_progress", "blocked"):
                chains.append(data)
        except Exception:
            continue
    return chains


def load_yesterday(date_str: str) -> dict | None:
    """Load yesterday's aggregated data for delta comparison."""
    yesterday = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_file = DAILY_DIR / f"{yesterday}.json"
    if yesterday_file.exists():
        try:
            return json.loads(yesterday_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def aggregate_day(date_str: str) -> dict:
    """Aggregate all data for a single day."""
    sessions = collect_sessions(date_str)
    skills_today = collect_skills_today()
    skill_log = collect_skill_log(date_str)
    commits = collect_git_commits(date_str)
    chains = collect_active_chains()

    # Extract accomplishments from sessions
    all_accomplishments = []
    for s in sessions:
        acc = s.get("accomplishments", {})
        if acc:
            all_accomplishments.append(acc)

    # Count stop reasons
    stop_reasons = {}
    for s in sessions:
        reason = s.get("stop_reason", "unknown")
        stop_reasons[reason] = stop_reasons.get(reason, 0) + 1

    # Count working directories
    cwds = {}
    for s in sessions:
        cwd = s.get("cwd", "unknown")
        cwds[cwd] = cwds.get(cwd, 0) + 1

    # Unique skills used
    skill_names = set()
    for entry in skill_log:
        skill_names.add(entry.get("skill", ""))
    for s in skills_today:
        # Format: "timestamp skill_name"
        parts = s.split(None, 1)
        if len(parts) >= 2:
            skill_names.add(parts[1])
    skill_names.discard("")

    # Files changed across sessions
    total_files_changed = sum(
        s.get("accomplishments", {}).get("files_changed", 0)
        for s in sessions
    )

    aggregated = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "sessions": {
            "count": len(sessions),
            "stop_reasons": stop_reasons,
            "working_dirs": cwds,
        },
        "accomplishments": {
            "commits": commits,
            "commit_count": len(commits),
            "skills_used": sorted(skill_names),
            "skill_count": len(skill_names),
            "files_changed": total_files_changed,
            "details": all_accomplishments,
        },
        "chains": {
            "active": [
                {
                    "chain_id": c.get("chain_id"),
                    "name": c.get("name"),
                    "step": f"{c.get('current_step', 0)}/{len(c.get('steps', []))}",
                    "current_step_name": c.get("steps", [])[c.get("current_step", 0)]
                        if c.get("current_step", 0) < len(c.get("steps", []))
                        else "done",
                    "status": c.get("status"),
                    "blocker": c.get("blocker"),
                    "updated_at": c.get("updated_at"),
                } for c in chains
            ],
            "active_count": len(chains),
        },
    }

    return aggregated


def render_dashboard(data: dict, yesterday: dict | None = None) -> str:
    """Render aggregated data as markdown dashboard."""
    date = data["date"]
    lines = [f"## Ops Pulse -- {date}", ""]

    # Sessions
    s = data["sessions"]
    reasons_str = ", ".join(f"{v} {k}" for k, v in s["stop_reasons"].items())
    lines.append(f"### Sessions ({s['count']})")
    if reasons_str:
        lines.append(f"- Stop reasons: {reasons_str}")
    for cwd, count in sorted(s["working_dirs"].items(), key=lambda x: -x[1]):
        lines.append(f"- {cwd} ({count}x)")
    lines.append("")

    # Accomplishments
    a = data["accomplishments"]
    lines.append(f"### Accomplishments")
    lines.append(f"- {a['commit_count']} git commits")
    for c in a["commits"][:5]:
        lines.append(f"  - `{c['hash']}` {c['message']} ({c['repo']})")
    lines.append(f"- {a['skill_count']} skills used: {', '.join(a['skills_used']) or 'none'}")
    if a["files_changed"]:
        lines.append(f"- {a['files_changed']} files changed")
    lines.append("")

    # Active Chains
    ch = data["chains"]
    if ch["active"]:
        lines.append(f"### Active Chains ({ch['active_count']})")
        for c in ch["active"]:
            # status_icon not needed - blocker info shown inline
            line = f"- [{c['name']}] Step {c['step']}: {c['current_step_name']}"
            if c["blocker"]:
                line += f" BLOCKED: {c['blocker']}"
            if c["updated_at"]:
                line += f" (updated {c['updated_at'][:16]})"
            lines.append(line)
        lines.append("")

    # Delta vs yesterday
    if yesterday:
        ya = yesterday.get("accomplishments", {})
        ys = yesterday.get("sessions", {})
        d_sessions = s["count"] - ys.get("count", 0)
        d_commits = a["commit_count"] - ya.get("commit_count", 0)
        d_skills = a["skill_count"] - ya.get("skill_count", 0)

        def fmt_delta(v):
            return f"+{v}" if v > 0 else str(v)

        lines.append("### Delta vs Yesterday")
        lines.append(
            f"- Sessions: {fmt_delta(d_sessions)} | "
            f"Commits: {fmt_delta(d_commits)} | "
            f"Skills: {fmt_delta(d_skills)}"
        )
        lines.append("")

    return "\n".join(lines)


def aggregate_week() -> str:
    """Aggregate last 7 days and render weekly summary."""
    today = datetime.now()
    week_data = []
    for i in range(7):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_file = DAILY_DIR / f"{date_str}.json"
        if daily_file.exists():
            try:
                week_data.append(json.loads(daily_file.read_text(encoding="utf-8")))
            except Exception:
                continue

    if not week_data:
        return "No daily data found for this week. Run `/pulse` first to generate today's data."

    total_sessions = sum(d["sessions"]["count"] for d in week_data)
    total_commits = sum(d["accomplishments"]["commit_count"] for d in week_data)
    all_skills = set()
    for d in week_data:
        all_skills.update(d["accomplishments"]["skills_used"])

    lines = [
        f"## Weekly Pulse -- {week_data[-1]['date']} to {week_data[0]['date']}",
        "",
        f"- {len(week_data)} days with data",
        f"- {total_sessions} sessions total",
        f"- {total_commits} commits total",
        f"- {len(all_skills)} unique skills: {', '.join(sorted(all_skills)) or 'none'}",
        "",
        "### Daily Breakdown",
    ]
    for d in reversed(week_data):
        lines.append(
            f"- {d['date']}: {d['sessions']['count']} sessions, "
            f"{d['accomplishments']['commit_count']} commits, "
            f"{d['accomplishments']['skill_count']} skills"
        )

    return "\n".join(lines)


def main():
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else "today"

    if mode == "--week":
        # First ensure today is aggregated
        today_str = datetime.now().strftime("%Y-%m-%d")
        data = aggregate_day(today_str)
        daily_file = DAILY_DIR / f"{today_str}.json"
        daily_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(aggregate_week())
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        data = aggregate_day(today_str)

        # Save daily JSON
        daily_file = DAILY_DIR / f"{today_str}.json"
        daily_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Load yesterday for delta
        yesterday = load_yesterday(today_str)

        # Render and print
        print(render_dashboard(data, yesterday))
        print(f"\nData saved to: {daily_file}")


if __name__ == "__main__":
    main()
