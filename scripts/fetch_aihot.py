#!/usr/bin/env python3
"""
Fetch AI HOT items from aihot.virxact.com public API.
Output: JSON array of standard Item objects to stdout.
"""

import json
import sys
import argparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

API_BASE = "https://aihot.virxact.com/api/public"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def build_since_str(since_hours: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_items(since_hours: int = 24, take: int = 100, query: str = None, mode: str = "selected") -> list:
    params = {"mode": mode, "since": build_since_str(since_hours), "take": take}
    if query:
        params["q"] = query

    url = f"{API_BASE}/items?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})

    try:
        with urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"[fetch_aihot] HTTP {e.code}: {e.reason}", file=sys.stderr)
        return []
    except URLError as e:
        print(f"[fetch_aihot] Network error: {e.reason}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"[fetch_aihot] JSON parse error: {e}", file=sys.stderr)
        return []

    # Normalize various response shapes: list / {items:[]} / {data:{items:[]}}
    if isinstance(raw, list):
        records = raw
    elif isinstance(raw, dict):
        records = raw.get("items") or raw.get("data", {}).get("items") or []
    else:
        records = []

    return [normalize(r) for r in records if isinstance(r, dict)]


def normalize(r: dict) -> dict:
    return {
        "title": r.get("title", "").strip(),
        "summary": r.get("summary") or r.get("description") or "",
        "url": r.get("url") or r.get("link") or "",
        "source": r.get("source") or "AI HOT",
        "published_at": r.get("published_at") or r.get("created_at") or "",
        "raw_category": r.get("category") or "",
        "marketing_categories": [],
        "matched_keywords": [],
        "marketing_score": 0,
        "priority": "",
        "impact": "",
        "recommended_action": "",
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch AI HOT items")
    parser.add_argument("--since-hours", type=int, default=24, dest="since_hours")
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--query", "-q", type=str, default=None)
    parser.add_argument("--take", type=int, default=100)
    parser.add_argument("--mode", type=str, default="selected", choices=["selected", "all"])
    args = parser.parse_args()

    since_hours = args.days * 24 if args.days else args.since_hours
    items = fetch_items(since_hours=since_hours, take=args.take, query=args.query, mode=args.mode)

    print(json.dumps(items, ensure_ascii=False, indent=2))
    print(f"[fetch_aihot] fetched {len(items)} items", file=sys.stderr)


if __name__ == "__main__":
    main()
