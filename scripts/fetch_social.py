#!/usr/bin/env python3
"""
Fetch social media and forum discussions about AI marketing.

Sources:
  - HackerNews:   Algolia search API (hn.algolia.com) — free, no auth, WORKING
  - Reddit:       public JSON API — CURRENTLY 403 (Reddit blocked unauthenticated
                  access in 2023; kept in code for when OAuth is added in V2)

NOT IMPLEMENTED:
  - X/Twitter:    requires paid API ($100+/mo)
  - LinkedIn:     no public API
  - Product Hunt: requires OAuth token

Output: JSON array of standard Item objects to stdout.
Social items carry extra fields: platform, community, engagement, discussion_signal.
"""

import json
import sys
import argparse
import re
import time
import threading
from queue import Queue, Empty
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

USER_AGENT = "Mozilla/5.0 (compatible; ai-marketing-hot/1.0; +https://github.com/jiguang9/ai-marketing-hot)"
TIMEOUT = 10

REDDIT_SUBREDDITS = [
    "marketing", "PPC", "SEO", "bigseo", "Entrepreneur",
    "SaaS", "shopify", "ecommerce", "DigitalMarketing", "socialmedia",
]

HN_QUERIES = [
    "AI marketing", "AI SEO", "Google Ads", "Meta Ads",
    "content marketing AI", "marketing automation", "AI UGC",
]

# Content must contain at least one of these to be marketing-relevant
MARKETING_FILTER_KW = [
    "ai", "chatgpt", "gpt", "llm", "claude", "gemini",
    "marketing", "seo", "ads", "advertising", "content",
    "google", "tiktok", "meta", "instagram", "shopify",
    "attribution", "roas", "conversion", "brand", "organic",
    "paid", "search", "email", "campaign", "funnel",
    "automation", "martech", "crm", "acquisition", "retention",
    "growth", "outbound", "inbound", "saas", "aeo", "geo", "llmo",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_social_item(title, summary, url, source, published_at,
                      platform, community, upvotes, comments) -> dict:
    parts = []
    if upvotes:
        parts.append(f"{upvotes} upvotes")
    if comments:
        parts.append(f"{comments} 评论")
    signal = f"{community} 讨论（{', '.join(parts)}）" if parts else f"{community} 讨论"

    return {
        "title": title,
        "summary": summary[:500] if summary else "",
        "url": url,
        "source": source,
        "published_at": published_at,
        "raw_category": "social",
        "platform": platform,
        "community": community,
        "engagement": {"upvotes": upvotes, "comments": comments},
        "discussion_signal": signal,
        "marketing_categories": [],
        "matched_keywords": [],
        "marketing_score": 0,
        "priority": "",
        "impact": "",
        "recommended_action": "",
        "audience": "",
    }


def _ts_to_iso(ts) -> str:
    try:
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


def _is_relevant(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in MARKETING_FILTER_KW)


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------

def fetch_reddit_subreddit(subreddit: str, since_epoch: float, result_queue: Queue):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=50"
    req = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"[fetch_social] Reddit r/{subreddit}: HTTP {e.code}", file=sys.stderr)
        result_queue.put([])
        return
    except Exception as e:
        print(f"[fetch_social] Reddit r/{subreddit}: {e}", file=sys.stderr)
        result_queue.put([])
        return

    items = []
    for post in data.get("data", {}).get("children", []):
        p = post.get("data", {})
        created = float(p.get("created_utc", 0))
        if created < since_epoch:
            continue

        title = (p.get("title") or "").strip()
        selftext = (p.get("selftext") or "").strip()
        if selftext in ("[removed]", "[deleted]"):
            selftext = ""
        permalink = "https://www.reddit.com" + (p.get("permalink") or "")

        if not _is_relevant(title + " " + selftext):
            continue

        items.append(_make_social_item(
            title=title,
            summary=selftext[:300],
            url=permalink,
            source=f"Reddit r/{subreddit}",
            published_at=_ts_to_iso(created),
            platform="Reddit",
            community=f"r/{subreddit}",
            upvotes=p.get("score", 0),
            comments=p.get("num_comments", 0),
        ))

    print(f"[fetch_social] Reddit r/{subreddit}: {len(items)} items", file=sys.stderr)
    result_queue.put(items)


# ---------------------------------------------------------------------------
# HackerNews (via Algolia)
# ---------------------------------------------------------------------------

def fetch_hn(query: str, since_epoch: float, result_queue: Queue):
    params = urlencode({
        "query": query,
        "tags": "story",
        "numericFilters": f"created_at_i>{int(since_epoch)}",
        "hitsPerPage": 30,
    })
    url = f"https://hn.algolia.com/api/v1/search?{params}"
    req = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[fetch_social] HN '{query}': {e}", file=sys.stderr)
        result_queue.put([])
        return

    items = []
    for hit in data.get("hits", []):
        title = (hit.get("title") or "").strip()
        if not title or not _is_relevant(title):
            continue

        obj_id = hit.get("objectID", "")
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={obj_id}"
        created_at = hit.get("created_at", "")
        pub = created_at[:19].replace(" ", "T") + "Z" if created_at else ""

        items.append(_make_social_item(
            title=title,
            summary="",
            url=link,
            source="Hacker News",
            published_at=pub,
            platform="Hacker News",
            community="Hacker News",
            upvotes=hit.get("points") or 0,
            comments=hit.get("num_comments") or 0,
        ))

    print(f"[fetch_social] HN '{query}': {len(items)} items", file=sys.stderr)
    result_queue.put(items)


# ---------------------------------------------------------------------------
# Concurrent fetch with daemon threads
# ---------------------------------------------------------------------------

def fetch_all(since_hours: int, query, max_workers: int, global_timeout: int) -> list:
    since_epoch = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).timestamp()
    result_queue: Queue = Queue()
    semaphore = threading.Semaphore(max_workers)

    def run(fn, *args):
        t = threading.Thread(target=_bounded(fn, semaphore, *args), daemon=True)
        t.start()
        return t

    def _bounded(fn, sem, *args):
        def inner():
            sem.acquire()
            try:
                fn(*args)
            finally:
                sem.release()
        return inner

    tasks = []
    subreddits = REDDIT_SUBREDDITS
    hn_queries = HN_QUERIES if not query else [query]

    for sub in subreddits:
        t = threading.Thread(
            target=lambda s=sub: (semaphore.acquire(), fetch_reddit_subreddit(s, since_epoch, result_queue), semaphore.release()),
            daemon=True,
        )
        t.start()
        tasks.append(t)

    for q in hn_queries:
        t = threading.Thread(
            target=lambda q=q: (semaphore.acquire(), fetch_hn(q, since_epoch, result_queue), semaphore.release()),
            daemon=True,
        )
        t.start()
        tasks.append(t)

    # If a specific query is given, skip reddit and only do HN + filtered reddit
    n_tasks = len(tasks)
    all_items = []
    collected = 0
    deadline = time.monotonic() + global_timeout

    while collected < n_tasks:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print(f"[fetch_social] Global timeout ({global_timeout}s) — {collected}/{n_tasks} sources done", file=sys.stderr)
            break
        try:
            items = result_queue.get(timeout=min(remaining, 0.5))
            all_items.extend(items)
            collected += 1
        except Empty:
            pass

    # Deduplicate by URL
    seen: set = set()
    unique = []
    for item in all_items:
        u = item.get("url", "")
        if u not in seen:
            seen.add(u)
            unique.append(item)

    return unique


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch social media discussions")
    parser.add_argument("--since-hours", type=int, default=24, dest="since_hours")
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--query", "-q", type=str, default=None,
                        help="Specific search query (HN only in focused mode)")
    parser.add_argument("--max-workers", type=int, default=8, dest="max_workers")
    parser.add_argument("--timeout", type=int, default=30, dest="global_timeout")
    args = parser.parse_args()

    since_hours = args.days * 24 if args.days else args.since_hours
    items = fetch_all(since_hours, args.query, args.max_workers, args.global_timeout)

    print(json.dumps(items, ensure_ascii=False, indent=2))
    print(f"[fetch_social] total {len(items)} items", file=sys.stderr)


if __name__ == "__main__":
    main()
