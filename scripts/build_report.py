#!/usr/bin/env python3
"""
Generate Chinese Markdown marketing report from ranked items.
Supports modes: daily, weekly, platform, opportunities.
"""

import json
import sys
import argparse
from datetime import datetime, timezone

PRIORITY_ORDER = ["立即关注", "本周跟进", "保持观察", "低优先级"]


def load_items(path: str) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[build_report] Error loading {path}: {e}", file=sys.stderr)
        return []


def format_time_label(since_hours: int) -> str:
    if since_hours <= 24:
        return "最近 24 小时"
    if since_hours <= 72:
        return f"最近 {since_hours // 24} 天"
    return f"最近 {since_hours // 24} 天（约 {since_hours // 168} 周）"


def format_published(pub: str) -> str:
    if not pub:
        return "时间未知"
    try:
        dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        # Convert to Beijing time (UTC+8)
        from datetime import timedelta
        dt_beijing = dt + timedelta(hours=8)
        now_beijing = datetime.now(timezone.utc) + timedelta(hours=8)
        delta = now_beijing - dt_beijing
        hours = int(delta.total_seconds() / 3600)
        if hours < 1:
            return "刚刚"
        if hours < 24:
            return f"{hours} 小时前"
        days = hours // 24
        return f"{days} 天前（{dt_beijing.strftime('%m/%d %H:%M')} 北京时间）"
    except Exception:
        return pub[:10]


def render_item(item: dict, index: int) -> str:
    title = item.get("title", "无标题")
    source = item.get("source", "未知来源")
    published = format_published(item.get("published_at", ""))
    categories = item.get("marketing_categories", [])
    cat_str = " / ".join(categories) if categories else "未分类"
    score = item.get("marketing_score", 0)
    impact = item.get("impact", "待评估")
    action = item.get("recommended_action", "待确定")
    url = item.get("url", "")
    summary = item.get("summary", "")

    lines = [f"### {index}. {title}"]
    if summary:
        lines.append(f"> {summary[:200]}{'…' if len(summary) > 200 else ''}")
        lines.append("")
    lines.append(f"- **来源**：{source}　**时间**：{published}　**评分**：{score}/100")
    lines.append(f"- **分类**：{cat_str}")
    lines.append(f"- **营销影响**：{impact}")
    lines.append(f"- **建议动作**：{action}")
    if url:
        lines.append(f"- **原文**：[查看原文]({url})")
    return "\n".join(lines)


def build_one_liner(items: list) -> str:
    if not items:
        return "暂无高优先级热点，市场相对平静。"
    top = items[0]
    cat = top.get("marketing_categories", ["通用"])[0] if top.get("marketing_categories") else "通用"
    cat_map = {
        "platform_changes": "平台规则",
        "seo_aeo": "AI 搜索",
        "paid_ads": "广告投放",
        "content_creative": "内容创作",
        "social_growth": "社媒增长",
        "ecommerce": "电商转化",
        "crm_martech": "MarTech",
        "brand_campaigns": "品牌营销",
        "creator_influencer": "达人生态",
        "research_insight": "行业洞察",
        "tools_launches": "工具发布",
    }
    cat_label = cat_map.get(cat, cat)
    title = top.get("title", "")[:40]
    urgent_count = sum(1 for i in items if i.get("priority") == "立即关注")
    return f"今日最值得关注的是「{cat_label}」动态：{title}…，共 {urgent_count} 条立即关注项。"


def build_trends(items: list) -> list[str]:
    from collections import Counter
    cat_counter: Counter = Counter()
    for item in items[:30]:
        for cat in item.get("marketing_categories", []):
            cat_counter[cat] += 1
    if not cat_counter:
        return ["暂无足够数据生成趋势判断。"]
    trends = []
    top_cats = cat_counter.most_common(3)
    cat_map = {
        "platform_changes": "平台算法与广告系统",
        "seo_aeo": "AI 搜索与 AEO/GEO",
        "paid_ads": "付费广告与归因",
        "content_creative": "AI 内容与创意生产",
        "social_growth": "社媒增长",
        "ecommerce": "电商与社交购物",
        "crm_martech": "MarTech 与自动化",
        "brand_campaigns": "品牌营销案例",
        "creator_influencer": "创作者经济",
        "research_insight": "行业研究洞察",
        "tools_launches": "AI 营销工具",
    }
    for cat, count in top_cats:
        label = cat_map.get(cat, cat)
        trends.append(f"**{label}** 热度最高（{count} 条），值得重点关注。")
    return trends


def build_action_checklist(items: list) -> list[str]:
    urgent = [i for i in items if i.get("priority") == "立即关注"][:5]
    if not urgent:
        return ["暂无紧急行动项，保持观察即可。"]
    actions = []
    for item in urgent:
        action = item.get("recommended_action", "")
        title = item.get("title", "")[:30]
        if action:
            actions.append(f"[ ] {action}（来自：{title}…）")
    return actions


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------

def report_daily(items: list, since_hours: int = 24, failed_sources: list = None) -> str:
    now_str = (datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")
    time_label = format_time_label(since_hours)

    urgent = [i for i in items if i.get("priority") == "立即关注"]
    weekly = [i for i in items if i.get("priority") == "本周跟进"]
    watch = [i for i in items if i.get("priority") == "保持观察"]

    lines = [
        "# AI 营销热点简报",
        "",
        f"**时间范围**：{time_label}　**生成时间**：{now_str}",
        f"**数据来源**：AI HOT + 营销官方源 + 行业媒体　**共收录**：{len(items)} 条",
    ]

    if failed_sources:
        lines.append(f"\n> ⚠️ 以下源未能获取：{', '.join(failed_sources)}")

    lines += ["", "---", "", "## 一句话总览", "", build_one_liner(items), ""]

    if urgent:
        lines += ["---", "", "## 立即关注", ""]
        for i, item in enumerate(urgent[:8], 1):
            lines.append(render_item(item, i))
            lines.append("")

    if weekly:
        lines += ["---", "", "## 本周跟进", ""]
        for i, item in enumerate(weekly[:6], 1):
            lines.append(render_item(item, i))
            lines.append("")

    if watch:
        lines += ["---", "", "## 保持观察", ""]
        for item in watch[:4]:
            title = item.get("title", "")
            source = item.get("source", "")
            url = item.get("url", "")
            cat = (item.get("marketing_categories") or ["未分类"])[0]
            link = f"[{title}]({url})" if url else title
            lines.append(f"- {link}（{source} · {cat}）")
        lines.append("")

    trends = build_trends(items)
    lines += ["---", "", "## 趋势判断", ""]
    for i, t in enumerate(trends, 1):
        lines.append(f"{i}. {t}")
    lines.append("")

    checklist = build_action_checklist(items)
    lines += ["---", "", "## 给营销团队的行动清单", ""]
    for action in checklist:
        lines.append(action)
    lines.append("")

    return "\n".join(lines)


def report_opportunities(items: list, since_hours: int = 24) -> str:
    time_label = format_time_label(since_hours)
    high = [i for i in items if i.get("marketing_score", 0) >= 60][:10]

    lines = [
        "# AI 营销机会清单",
        "",
        f"**时间范围**：{time_label}　**筛选条件**：评分 ≥ 60 分",
        "",
        "---",
        "",
    ]

    if not high:
        lines.append("当前时间窗内暂无高分营销机会，建议扩大时间范围（--since-hours 72）。")
        return "\n".join(lines)

    for i, item in enumerate(high, 1):
        score = item.get("marketing_score", 0)
        priority = item.get("priority", "")
        lines.append(f"## 机会 {i}　`{score}分` `{priority}`")
        lines.append("")
        lines.append(render_item(item, i))
        lines.append("")

    return "\n".join(lines)


def report_platform(items: list, platform: str, since_hours: int = 24) -> str:
    platform_lower = platform.lower()
    filtered = [
        i for i in items
        if platform_lower in (i.get("title", "") + i.get("summary", "") + i.get("source", "")).lower()
    ]
    time_label = format_time_label(since_hours)

    lines = [
        f"# {platform} 营销动态专题",
        "",
        f"**时间范围**：{time_label}　**共 {len(filtered)} 条相关内容**",
        "",
        "---",
        "",
    ]

    if not filtered:
        lines.append(f"当前时间窗内未检测到 {platform} 相关营销动态。")
        return "\n".join(lines)

    for i, item in enumerate(filtered[:10], 1):
        lines.append(render_item(item, i))
        lines.append("")

    return "\n".join(lines)


def report_weekly(items: list) -> str:
    return report_daily(items, since_hours=168)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build AI marketing report")
    parser.add_argument("--input", "-i", required=True, help="Path to ranked JSON file")
    parser.add_argument("--mode", choices=["daily", "weekly", "platform", "opportunities"], default="daily")
    parser.add_argument("--platform", default="", help="Platform name for platform mode")
    parser.add_argument("--since-hours", type=int, default=24, dest="since_hours")
    parser.add_argument("--output", "-o", default=None, help="Output file (default: stdout)")
    args = parser.parse_args()

    items = load_items(args.input)
    if not items:
        print("[build_report] No items to report.", file=sys.stderr)
        sys.exit(1)

    if args.mode == "daily":
        report = report_daily(items, args.since_hours)
    elif args.mode == "weekly":
        report = report_weekly(items)
    elif args.mode == "opportunities":
        report = report_opportunities(items, args.since_hours)
    elif args.mode == "platform":
        if not args.platform:
            print("[build_report] --platform required for platform mode", file=sys.stderr)
            sys.exit(1)
        report = report_platform(items, args.platform, args.since_hours)
    else:
        report = report_daily(items, args.since_hours)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[build_report] Written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
