#!/usr/bin/env python3
"""Collect Claude Code telemetry data for a release cycle.

Reads ~/.claude/usage.db for session totals and the per-agent subagent
JSONL files for per-turn token breakdowns.  Writes a structured
docs/releases/telemetry-<release>.json file that the token-analyst agent
can consume using the Read tool — no Bash access required by the agent.

The orchestrator runs this script (via Bash) before dispatching the
token-analyst.  The token-analyst then reads the resulting JSON file.

Usage
-----
    # By session ID (most precise — run after all release sessions complete):
    python scripts/collect_telemetry.py --release v0.7.0 \\
        --session 1a2b056d-22e2-4fd8-80e2-8c1eedd308c1

    # By date range (all sessions on one or more release days):
    python scripts/collect_telemetry.py --release v0.7.0 \\
        --date-from 2026-05-10 --date-to 2026-05-11

    # Multiple session IDs (two-session delivery):
    python scripts/collect_telemetry.py --release v0.7.0 \\
        --session SESSION_ID_1 SESSION_ID_2

    # Override output path:
    python scripts/collect_telemetry.py --release v0.7.0 \\
        --session SESSION_ID --out /tmp/telem.json

Output JSON schema
------------------
{
  "generated_at": "<ISO-8601 UTC>",
  "release": "v0.7.0",
  "sessions": [
    {
      "session_id": "...",
      "project_name": "...",
      "first_timestamp": "...",
      "last_timestamp": "...",
      "git_branch": "...",
      "total_input_tokens": 0,
      "total_output_tokens": 0,
      "total_cache_read": 0,
      "total_cache_creation": 0,
      "model": "...",
      "turn_count": 0,
      "subagents": [
        {
          "agent_id": "agent-<hex>",
          "agent_type": "developer",
          "description": "3.D2 — format_detector.py implementation",
          "input_tokens": 0,
          "output_tokens": 0,
          "cache_read_tokens": 0,
          "cache_creation_tokens": 0,
          "turns": 0
        }
      ]
    }
  ],
  "summary": {
    "session_count": 1,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cache_read": 0,
    "total_cache_creation": 0,
    "agent_dispatch_count": 0
  }
}
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _telemetry_paths() -> tuple[Path, str, Path]:
    """Return (db_path, project_name, subagent_root) for the current working directory.

    Derives all paths from Path.cwd() — no hardcoded usernames or repo locations.
    The encoding rules mirror what Claude Code uses when naming project directories.
    """
    home = Path.home()
    db = home / ".claude" / "usage.db"

    cwd = Path.cwd()
    # Claude Code records project_name as the last two path components joined with "/".
    project_name = "/".join(cwd.parts[-2:])

    # Claude Code encodes the full cwd as a directory name by replacing path
    # separators and the drive colon with "-", stripping any leading "-", then
    # lower-casing the first character (the Windows drive letter).
    encoded = str(cwd).replace(":", "-").replace("\\", "-").replace("/", "-").lstrip("-")
    if encoded:
        encoded = encoded[0].lower() + encoded[1:]
    subagent_root = home / ".claude" / "projects" / encoded

    return db, project_name, subagent_root


def _subagent_tokens(jsonl_path: Path) -> dict[str, int]:
    """Sum per-turn token usage from a subagent JSONL conversation file.

    Each assistant turn in the file carries a usage dict with input_tokens,
    output_tokens, cache_read_input_tokens, and cache_creation_input_tokens.
    Turns that fail to parse are silently skipped.
    """
    totals: dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "turns": 0,
    }
    if not jsonl_path.exists():
        return totals

    for raw in jsonl_path.read_text(encoding="utf-8").splitlines():
        try:
            obj: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if obj.get("type") != "assistant":
            continue

        msg = obj.get("message", {})
        if not isinstance(msg, dict):
            continue

        usage = msg.get("usage", {})
        totals["input_tokens"] += usage.get("input_tokens", 0)
        totals["output_tokens"] += usage.get("output_tokens", 0)
        totals["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)
        totals["cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
        totals["turns"] += 1

    return totals


def _collect_subagents(session_dir: Path) -> list[dict[str, Any]]:
    """Return per-agent token data for every subagent spawned in a session directory."""
    subagents_dir = session_dir / "subagents"
    if not subagents_dir.exists():
        return []

    agents: list[dict[str, Any]] = []
    for meta_file in sorted(subagents_dir.glob("*.meta.json")):
        # The JSONL sibling file name is <agent-id>.jsonl (strip the .meta.json suffix).
        agent_id = meta_file.name.replace(".meta.json", "")
        try:
            meta: dict[str, Any] = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        token_data = _subagent_tokens(meta_file.parent / (agent_id + ".jsonl"))
        agents.append(
            {
                "agent_id": agent_id,
                "agent_type": meta.get("agentType", ""),
                "description": meta.get("description", ""),
                **token_data,
            }
        )

    return agents


def collect(
    release: str,
    session_ids: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Collect telemetry for a release cycle and return the structured data dict.

    Parameters
    ----------
    release:     Release version string, e.g. "v0.7.0".
    session_ids: Explicit session UUIDs to include.  When provided, date filters
                 are ignored.
    date_from:   ISO date string "YYYY-MM-DD" — include sessions starting on or
                 after this date.
    date_to:     ISO date string "YYYY-MM-DD" — include sessions ending on or
                 before this date (inclusive of the full day).
    """
    db_path, project_name, subagent_root = _telemetry_paths()

    if not db_path.exists():
        raise FileNotFoundError(
            f"Claude Code usage.db not found at {db_path}.  "
            "Ensure Claude Code has been run at least once on this machine."
        )

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()

        if session_ids:
            placeholders = ",".join("?" * len(session_ids))
            cur.execute(
                f"""
                SELECT session_id, project_name, first_timestamp, last_timestamp,
                       git_branch, total_input_tokens, total_output_tokens,
                       total_cache_read, total_cache_creation, model, turn_count
                FROM sessions
                WHERE session_id IN ({placeholders})
                ORDER BY first_timestamp
                """,
                session_ids,
            )
        else:
            params: list[Any] = [project_name]
            filters = "WHERE project_name = ?"
            if date_from:
                filters += " AND first_timestamp >= ?"
                params.append(date_from)
            if date_to:
                filters += " AND last_timestamp <= ?"
                params.append(date_to + "T23:59:59")
            cur.execute(
                f"""
                SELECT session_id, project_name, first_timestamp, last_timestamp,
                       git_branch, total_input_tokens, total_output_tokens,
                       total_cache_read, total_cache_creation, model, turn_count
                FROM sessions
                {filters}
                ORDER BY first_timestamp
                """,
                params,
            )

        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        hint = (
            f"sessions for project '{project_name}'"
            if not session_ids
            else f"sessions with IDs: {session_ids}"
        )
        raise ValueError(
            f"No sessions found matching {hint}.  "
            "Use --session to specify by UUID, or --date-from/--date-to to filter by date."
        )

    sessions: list[dict[str, Any]] = []
    total_in = total_out = total_cr = total_cw = 0

    for row in rows:
        sid: str = row["session_id"]
        subagents = _collect_subagents(subagent_root / sid)

        sessions.append(
            {
                "session_id": sid,
                "project_name": row["project_name"],
                "first_timestamp": row["first_timestamp"],
                "last_timestamp": row["last_timestamp"],
                "git_branch": row["git_branch"],
                "total_input_tokens": row["total_input_tokens"],
                "total_output_tokens": row["total_output_tokens"],
                "total_cache_read": row["total_cache_read"],
                "total_cache_creation": row["total_cache_creation"],
                "model": row["model"],
                "turn_count": row["turn_count"],
                "subagents": subagents,
            }
        )
        total_in += row["total_input_tokens"]
        total_out += row["total_output_tokens"]
        total_cr += row["total_cache_read"]
        total_cw += row["total_cache_creation"]

    agent_count = sum(len(s["subagents"]) for s in sessions)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "release": release,
        "sessions": sessions,
        "summary": {
            "session_count": len(sessions),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_cache_read": total_cr,
            "total_cache_creation": total_cw,
            "agent_dispatch_count": agent_count,
        },
    }


def _print_summary(data: dict[str, Any]) -> None:
    s = data["summary"]
    print(f"\nTelemetry collected — {data['release']}")
    print(f"  Sessions:         {s['session_count']}")
    print(f"  Agent dispatches: {s['agent_dispatch_count']}")
    print(f"  Input tokens:     {s['total_input_tokens']:>12,}")
    print(f"  Output tokens:    {s['total_output_tokens']:>12,}")
    print(f"  Cache read:       {s['total_cache_read']:>12,}")
    print(f"  Cache write:      {s['total_cache_creation']:>12,}")

    for session in data["sessions"]:
        ts = session["first_timestamp"][:16]
        print(
            f"\n  Session {session['session_id'][:8]}  "
            f"{ts}  branch={session['git_branch']}  "
            f"turns={session['turn_count']}"
        )
        for agent in session["subagents"]:
            atype = agent["agent_type"]
            desc = agent["description"][:50]
            out = agent["output_tokens"]
            cr = agent["cache_read_tokens"]
            print(f"    {atype:<22} {desc:<51} out={out:>7,}  cache_read={cr:>10,}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Claude Code telemetry for a release cycle.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--release",
        required=True,
        metavar="vX.Y.Z",
        help="Release version tag, e.g. v0.7.0",
    )
    parser.add_argument(
        "--session",
        nargs="+",
        metavar="SESSION_ID",
        help="One or more session UUIDs to include.  Overrides date filters.",
    )
    parser.add_argument(
        "--date-from",
        metavar="YYYY-MM-DD",
        help="Include sessions starting on or after this date.",
    )
    parser.add_argument(
        "--date-to",
        metavar="YYYY-MM-DD",
        help="Include sessions ending on or before this date (full day inclusive).",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Output JSON path (default: docs/releases/telemetry-<release>.json)",
    )

    args = parser.parse_args()

    if not args.session and not (args.date_from or args.date_to):
        parser.error(
            "Provide at least one of --session, --date-from, or --date-to to scope the collection."
        )

    try:
        data = collect(
            release=args.release,
            session_ids=args.session,
            date_from=args.date_from,
            date_to=args.date_to,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    out_path = (
        Path(args.out) if args.out else Path("docs/releases") / f"telemetry-{args.release}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    _print_summary(data)
    print(f"\n  Written to: {out_path}")


if __name__ == "__main__":
    main()
