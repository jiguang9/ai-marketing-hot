#!/usr/bin/env python3
"""
Fetch items from marketing sources defined in references/sources.yaml.
Supports RSS 2.0 and Atom feeds. Uses stdlib only.
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
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            # New list item
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
    # ISO 8601
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass
    # RFC 2822 (RSS pubDate)
    try:
        dt = parsedate_to_datetime(s)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    return s


def is_within_hours(date_str: str, hours: int) -> bool:
    if not date_str:
        return True  # unknown date – include it
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return dt >= cutoff
    except Exception:
        return True


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return html.unescape(text.strip())


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

    tag = root.tag.lower()

    # Atom feed
    if "atom" in tag or root.tag == f"{{{ATOM_NS}}}feed":
        ns = ATOM_NS
        for entry in root.findall(f"{{{ns}}}entry"):
            title = (entry.findtext(f"{{{ns}}}title") or "").strip()
            link_el = entry.find(f"{{{ns}}}link")
            url = (link_el.get("href") if link_el is not None else "") or ""
            summary = strip_html(entry.findtext(f"{{{ns}}}summary") or entry.findtext(f"{{{ns}}}content") or "")
            updated = parse_date(entry.findtext(f"{{{ns}}}updated") or entry.findtext(f"{{{ns}}}published") or "")
            if title and url:
                items.append(_make_item(title, summary[:500], url, source_name, updated))
        return items

    # RSS 2.0
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        description = strip_html(item.findtext("description") or "")
        pub_date = parse_date(item.findtext("pubDate") or "")
        if title and url:
            items.append(_make_item(title, description[:500], url, source_name, pub_date))

    return items


def _make_item(title, summary, url, source, published_at) -> dict:
    return {
        "title": html.unescape(title),
        "summary": html.unescape(summary),
        "url": html.unescape(url),
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
# HTTP fetch
# ---------------------------------------------------------------------------

def fetch_rss(source: dict) -> list:
    name = source.get("name", "unknown")
    url = source.get("url", "")
    if not url:
        return []

    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, text/xml, */*"})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            content = resp.read()
    except HTTPError as e:
        print(f"[fetch_sources] HTTP {e.code} – {name} ({url})", file=sys.stderr)
        return []
    except URLError as e:
        print(f"[fetch_sources] Network error – {name}: {e.reason}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[fetch_sources] Error – {name}: {e}", file=sys.stderr)
        return []

    return parse_feed(content, name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch marketing source items")
    parser.add_argument("--since-hours", type=int, default=24, dest="since_hours")
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument(
        "--sources-file",
        default=os.path.join(os.path.dirname(__file__), "..", "references", "sources.yaml"),
    )
    parser.add_argument("--max-workers", type=int, default=6, help="Concurrent RSS fetch workers")
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
    failed = []
    all_items = []

    worker_count = max(1, min(args.max_workers, len(rss_sources) or 1))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_source = {executor.submit(fetch_rss, source): source for source in rss_sources}
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                items = future.result()
            except Exception as e:
                print(f"[fetch_sources] Error – {source.get('name', '?')}: {e}", file=sys.stderr)
                items = []

            if not items:
                failed.append(source.get("name", "?"))
                continue

            items = [i for i in items if is_within_hours(i["published_at"], since_hours)]
            all_items.extend(items)
            print(f"[fetch_sources] {source['name']}: {len(items)} items", file=sys.stderr)

    if failed:
        print(f"[fetch_sources] Failed sources: {', '.join(failed)}", file=sys.stderr)

    print(json.dumps(all_items, ensure_ascii=False, indent=2))
    print(f"[fetch_sources] total {len(all_items)} items from {len(rss_sources) - len(failed)} sources", file=sys.stderr)


if __name__ == "__main__":
    main()
