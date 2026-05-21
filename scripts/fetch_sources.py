#!/usr/bin/env python3
"""
Fetch items from marketing sources defined in references/sources.yaml.
Supports RSS 2.0 and Atom feeds. Uses stdlib only (concurrent.futures for parallel fetching).
Output: JSON array of standard Item objects to stdout.
"""

import json
import sys
import argparse
import re
import os
import html
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime
import threading
import time
from queue import Queue, Empty

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
ATOM_NS = "http://www.w3.org/2005/Atom"
TIMEOUT = 12


# ---------------------------------------------------------------------------
# Minimal YAML parser – handles the specific structure of sources.yaml
# ---------------------------------------------------------------------------

def _yaml_value(v: str):
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if v == "true":
        return True
    if v == "false":
        return False
    if v.startswith("[") and v.endswith("]"):
        parts = v[1:-1].split(",")
        return [p.strip().strip("\"'") for p in parts if p.strip()]
    try:
        return int(v)
    except ValueError:
        return v


def load_sources_yaml(path: str) -> list:
    sources = []
    current = None
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if line == "sources:":
                continue
            if re.match(r"^  - ", line):
                if current is not None:
                    sources.append(current)
                current = {}
                rest = line[4:]
                if ": " in rest:
                    k, _, v = rest.partition(": ")
                    current[k.strip()] = _yaml_value(v)
            elif re.match(r"^    \w", line) and current is not None:
                rest = line.strip()
                if ": " in rest:
                    k, _, v = rest.partition(": ")
                    current[k.strip()] = _yaml_value(v)
    if current is not None:
        sources.append(current)
    return sources


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_date(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(s)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    return s


def is_within_hours(date_str: str, hours: int) -> bool:
    if not date_str:
        return True
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return dt >= cutoff
    except Exception:
        return True


# ---------------------------------------------------------------------------
# HTML stripping and entity unescaping
# ---------------------------------------------------------------------------

def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text(text: str) -> str:
    return html.unescape(strip_html(text))


# ---------------------------------------------------------------------------
# RSS / Atom parsing
# ---------------------------------------------------------------------------

def parse_feed(content: bytes, source_name: str) -> list:
    items = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"[fetch_sources] XML parse error ({source_name}): {e}", file=sys.stderr)
        return items

    # Atom feed
    if root.tag in (f"{{{ATOM_NS}}}feed", "feed") or "atom" in root.tag.lower():
        ns = ATOM_NS
        for entry in root.findall(f"{{{ns}}}entry"):
            title = clean_text(entry.findtext(f"{{{ns}}}title") or "")
            link_el = entry.find(f"{{{ns}}}link")
            url = html.unescape((link_el.get("href") if link_el is not None else "") or "")
            summary = clean_text(
                entry.findtext(f"{{{ns}}}summary") or entry.findtext(f"{{{ns}}}content") or ""
            )
            updated = parse_date(
                entry.findtext(f"{{{ns}}}updated") or entry.findtext(f"{{{ns}}}published") or ""
            )
            if title and url:
                items.append(_make_item(title, summary[:500], url, source_name, updated))
        return items

    # RSS 2.0
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title") or "")
        url = html.unescape((item.findtext("link") or "").strip())
        description = clean_text(item.findtext("description") or "")
        pub_date = parse_date(item.findtext("pubDate") or "")
        if title and url:
            items.append(_make_item(title, description[:500], url, source_name, pub_date))

    return items


def _make_item(title, summary, url, source, published_at) -> dict:
    return {
        "title": title,
        "summary": summary,
        "url": url,
        "source": source,
        "published_at": published_at,
        "raw_category": "rss",
        "marketing_categories": [],
        "matched_keywords": [],
        "marketing_score": 0,
        "priority": "",
        "impact": "",
        "recommended_action": "",
    }


# ---------------------------------------------------------------------------
# HTTP fetch (per-source, isolated)
# ---------------------------------------------------------------------------

def fetch_rss(source: dict) -> list:
    name = source.get("name", "unknown")
    url = source.get("url", "")
    if not url:
        return []

    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, text/xml, */*",
        },
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            content = resp.read()
    except HTTPError as e:
        print(f"[fetch_sources] HTTP {e.code} – {name}", file=sys.stderr)
        return []
    except URLError as e:
        print(f"[fetch_sources] Network error – {name}: {e.reason}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[fetch_sources] Error – {name}: {e}", file=sys.stderr)
        return []

    return parse_feed(content, name)


# ---------------------------------------------------------------------------
# Concurrent fetch with daemon threads (process exits cleanly after timeout)
# ---------------------------------------------------------------------------

def fetch_all(rss_sources: list, since_hours: int, max_workers: int, global_timeout: int = 30) -> tuple:
    result_queue: Queue = Queue()
    semaphore = threading.Semaphore(max_workers)

    def worker(source):
        semaphore.acquire()
        try:
            items = fetch_rss(source)
            result_queue.put((source.get("name", "?"), items))
        finally:
            semaphore.release()

    for source in rss_sources:
        t = threading.Thread(target=worker, args=(source,), daemon=True)
        t.start()

    all_items = []
    failed = []
    collected: set = set()
    deadline = time.monotonic() + global_timeout

    while len(collected) < len(rss_sources):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            name, items = result_queue.get(timeout=min(remaining, 0.5))
            collected.add(name)
            if items:
                filtered = [i for i in items if is_within_hours(i["published_at"], since_hours)]
                all_items.extend(filtered)
                print(f"[fetch_sources] {name}: {len(filtered)} items", file=sys.stderr)
            else:
                failed.append(name)
        except Empty:
            pass

    timed_out = [s.get("name", "?") for s in rss_sources if s.get("name", "?") not in collected]
    if timed_out:
        print(
            f"[fetch_sources] Global timeout ({global_timeout}s) – skipping: {', '.join(timed_out)}",
            file=sys.stderr,
        )
        failed.extend(timed_out)

    return all_items, failed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch marketing source items")
    parser.add_argument("--since-hours", type=int, default=24, dest="since_hours")
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--max-workers", type=int, default=6, dest="max_workers")
    parser.add_argument("--timeout", type=int, default=30, dest="global_timeout",
                        help="Global timeout in seconds for all RSS fetches (default: 30)")
    parser.add_argument(
        "--sources-file",
        default=os.path.join(os.path.dirname(__file__), "..", "references", "sources.yaml"),
    )
    args = parser.parse_args()

    since_hours = args.days * 24 if args.days else args.since_hours
    sources_path = os.path.abspath(args.sources_file)

    try:
        all_sources = load_sources_yaml(sources_path)
    except FileNotFoundError:
        print(f"[fetch_sources] sources.yaml not found: {sources_path}", file=sys.stderr)
        print("[]")
        return

    rss_sources = [s for s in all_sources if s.get("type") == "rss" and s.get("enabled", True)]
    all_items, failed = fetch_all(rss_sources, since_hours, args.max_workers, args.global_timeout)

    if failed:
        print(f"[fetch_sources] Failed sources: {', '.join(failed)}", file=sys.stderr)

    print(json.dumps(all_items, ensure_ascii=False, indent=2))
    print(
        f"[fetch_sources] total {len(all_items)} items "
        f"from {len(rss_sources) - len(failed)}/{len(rss_sources)} sources",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
