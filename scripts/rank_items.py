#!/usr/bin/env python3
"""
Merge, deduplicate, classify, and score marketing items.
Input:  one or more JSON files (arrays of Item objects) as positional args,
        or JSON array on stdin if no files given.
Output: enriched, sorted JSON array to stdout.
"""

import json
import sys
import re
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Taxonomy – marketing category keywords
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "platform_changes": [
        "algorithm", "policy", "platform update", "ads policy", "feed change",
        "google ads", "meta ads", "tiktok ads", "youtube ads", "linkedin ads",
        "amazon ads", "apple ads", "snap ads", "pinterest ads",
        "广告政策", "平台变化", "算法更新", "投放系统", "广告系统",
    ],
    "seo_aeo": [
        "seo", "aeo", "geo", "llmo", "ai overview", "ai search", "search ranking",
        "generative search", "sge", "search generative", "indexing", "crawl",
        "perplexity", "search engine", "bing", "organic search", "serp",
        "搜索排名", "ai搜索", "搜索算法", "语义搜索", "搜索引擎", "生成式搜索",
    ],
    "paid_ads": [
        "roas", "attribution", "bidding", "cpc", "cpm", "ctr", "conversion tracking",
        "programmatic", "rtb", "dsp", "performance max", "pmax", "smart bidding",
        "retargeting", "remarketing", "lookalike", "lead generation", "demand gen",
        "广告投放", "广告归因", "出价策略", "投放优化", "获客成本", "转化归因",
    ],
    "content_creative": [
        "content creation", "copywriting", "ai writing", "image generation",
        "video generation", "creative ai", "sora", "dall-e", "midjourney",
        "stable diffusion", "runway", "generative ai", "content automation",
        "内容创作", "文案生成", "创意生成", "ai写作", "视频生成", "图片生成",
    ],
    "social_growth": [
        "instagram", "reels", "shorts", "viral", "growth hacking", "organic reach",
        "social media", "engagement", "community", "user generated", "ugc",
        "tiktok trend", "twitter", "x.com", "threads",
        "社媒", "社交媒体", "增长", "私域", "流量", "涨粉",
    ],
    "ecommerce": [
        "ecommerce", "e-commerce", "shopify", "amazon", "shopping", "checkout",
        "product listing", "commerce", "retail", "dtc", "direct to consumer",
        "tiktok shop", "live shopping", "social commerce", "conversion rate",
        "电商", "转化", "购物", "零售", "出海", "跨境", "独立站",
    ],
    "crm_martech": [
        "crm", "martech", "marketing automation", "hubspot", "salesforce", "klaviyo",
        "email marketing", "customer data", "cdp", "segmentation", "lifecycle",
        "marketing cloud", "adobe experience", "customer journey", "personalization",
        "营销自动化", "客户管理", "用户分层", "数据平台", "用户运营",
    ],
    "brand_campaigns": [
        "brand campaign", "brand awareness", "branded content", "sponsorship",
        "brand safety", "creative strategy", "campaign launch", "brand building",
        "品牌", "品牌案例", "品牌营销", "campaign", "创意策略",
    ],
    "creator_influencer": [
        "creator", "influencer", "ugc", "kol", "koc", "live streaming", "livestream",
        "creator economy", "affiliate", "collab", "brand deal", "sponsored",
        "创作者", "达人", "直播", "网红", "带货", "kol", "mcn",
    ],
    "research_insight": [
        "report", "research", "survey", "consumer insight", "trend report",
        "study", "statistics", "market research", "gartner", "forrester",
        "报告", "研究", "调研", "洞察", "趋势", "数据报告",
    ],
    "tools_launches": [
        "launch", "release", "new tool", "beta", "product launch", "new feature",
        "api", "integration", "plugin", "update", "now available", "general availability",
        "发布", "上线", "新工具", "新功能", "工具", "beta", "开放",
    ],
}

# Platform tier for scoring
MAJOR_PLATFORMS = ["google", "meta", "tiktok", "apple", "microsoft", "amazon", "openai", "anthropic"]
MID_PLATFORMS = ["linkedin", "twitter", "x.com", "shopify", "hubspot", "salesforce", "adobe", "canva", "klaviyo", "youtube", "instagram", "snap", "pinterest"]

# High-value marketing keywords for business impact score
HIGH_IMPACT_KW = ["ads", "advertising", "seo", "search ranking", "conversion", "roas", "attribution", "bidding", "checkout", "revenue", "广告", "转化", "搜索", "投放"]
MID_IMPACT_KW = ["content", "automation", "personalization", "recommendation", "crm", "email", "内容", "自动化", "私域"]

# Official source domains get credibility bonus
OFFICIAL_DOMAINS = [
    "blog.google", "developers.google.com", "about.fb.com", "business.facebook.com",
    "business.tiktok.com", "newsroom.tiktok.com", "business.linkedin.com",
    "blog.hubspot.com", "shopify.com/blog", "blog.adobe.com", "canva.com/newsroom",
]

# Impact template by category
IMPACT_TEMPLATES: dict[str, str] = {
    "platform_changes": "平台规则/算法变化，直接影响现有广告投放和内容分发策略",
    "seo_aeo": "影响搜索流量获取方式，AEO/GEO 时代下内容策略需同步调整",
    "paid_ads": "直接影响广告投放效率和预算分配，需评估现有出价策略是否适配",
    "content_creative": "改变内容生产成本和效率，可能影响竞争对手的内容产量",
    "social_growth": "影响社媒自然流量获取，关注触达率和互动率变化",
    "ecommerce": "影响电商转化链路，关注选品、落地页、支付体验的优化机会",
    "crm_martech": "影响营销自动化效率，评估现有工具栈是否需要更新",
    "brand_campaigns": "品牌侧案例，可参考借鉴其创意策略和投放组合",
    "creator_influencer": "影响达人/创作者合作方式，关注新兴平台和内容形式",
    "research_insight": "消费者洞察和行业趋势，用于支撑策略决策",
    "tools_launches": "新工具发布，评估是否能提升现有工作流效率",
}

ACTION_TEMPLATES: dict[str, str] = {
    "platform_changes": "立即检查现有广告账户是否受影响，更新投放策略",
    "seo_aeo": "审查现有内容是否符合 AI 搜索优化要求，补充结构化数据",
    "paid_ads": "A/B 测试新出价策略，监控关键转化指标变化",
    "content_creative": "评估该工具是否能替代或增强现有内容生产流程",
    "social_growth": "跟踪自然流量数据，考虑调整发布频次和内容形式",
    "ecommerce": "测试新的转化优化手段，关注竞品的跟进速度",
    "crm_martech": "评估与现有 CRM/自动化系统的集成可能性",
    "brand_campaigns": "提炼可复用的创意方法论，应用到下一个 campaign",
    "creator_influencer": "更新达人合作标准和内容 brief，适配新平台规则",
    "research_insight": "将关键数据纳入季度策略规划，更新用户画像",
    "tools_launches": "申请 beta 资格或安排产品演示，评估 ROI",
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_platform_impact(content: str, source: str) -> int:
    c = content.lower()
    s = source.lower()
    if any(p in c or p in s for p in MAJOR_PLATFORMS):
        return 22
    if any(p in c or p in s for p in MID_PLATFORMS):
        return 13
    return 5


def score_business_impact(content: str) -> int:
    c = content.lower()
    if any(k in c for k in HIGH_IMPACT_KW):
        return 26
    if any(k in c for k in MID_IMPACT_KW):
        return 15
    return 5


def score_action_window(content: str) -> int:
    c = content.lower()
    action_kw = ["launch", "release", "now available", "new feature", "update", "beta", "announced",
                 "发布", "上线", "新功能", "更新", "开放", "公测"]
    if any(k in c for k in action_kw):
        return 17
    return 6


def score_freshness(published_at: str) -> int:
    if not published_at:
        return 7
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if hours_ago < 6:
            return 15
        if hours_ago < 24:
            return 12
        if hours_ago < 72:
            return 8
        return 3
    except Exception:
        return 7


def score_credibility(url: str) -> int:
    if any(d in url for d in OFFICIAL_DOMAINS):
        return 10
    reputable = ["searchengineland.com", "adweek.com", "thedrum.com", "martech.org",
                 "socialmediatoday.com", "marketingbrew.com", "thinkwithgoogle.com"]
    if any(d in url for d in reputable):
        return 8
    return 5


def compute_score(item: dict) -> int:
    content = (item.get("title", "") + " " + item.get("summary", "")).lower()
    source = item.get("source", "")
    url = item.get("url", "")

    total = (
        score_platform_impact(content, source)
        + score_business_impact(content)
        + score_action_window(content)
        + score_freshness(item.get("published_at", ""))
        + score_credibility(url)
    )
    return min(total, 100)


def score_to_priority(score: int) -> str:
    if score >= 80:
        return "立即关注"
    if score >= 60:
        return "本周跟进"
    if score >= 40:
        return "保持观察"
    return "低优先级"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify(item: dict) -> tuple[list[str], list[str]]:
    content = (item.get("title", "") + " " + item.get("summary", "")).lower()
    categories = []
    matched = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        hits = [k for k in keywords if k in content]
        if hits:
            categories.append(cat)
            matched.extend(hits[:3])  # cap per category
    return categories or ["tools_launches"], list(dict.fromkeys(matched))  # dedup preserving order


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def normalize_url(url: str) -> str:
    url = url.split("?")[0].split("#")[0].rstrip("/").lower()
    url = re.sub(r"^https?://www\.", "https://", url)
    return url


def dedup(items: list) -> list:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out = []
    for item in items:
        url_key = normalize_url(item.get("url", ""))
        title_key = re.sub(r"\W+", "", item.get("title", "").lower())[:60]
        if url_key and url_key in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue
        if url_key:
            seen_urls.add(url_key)
        if title_key:
            seen_titles.add(title_key)
        out.append(item)
    return out


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

def enrich(item: dict) -> dict:
    categories, keywords = classify(item)
    score = compute_score(item)
    priority = score_to_priority(score)
    primary_cat = categories[0] if categories else "tools_launches"

    item["marketing_categories"] = categories
    item["matched_keywords"] = keywords
    item["marketing_score"] = score
    item["priority"] = priority
    item["impact"] = IMPACT_TEMPLATES.get(primary_cat, "待评估营销影响")
    item["recommended_action"] = ACTION_TEMPLATES.get(primary_cat, "进一步研究后确定行动方向")
    return item


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_items(paths: list[str]) -> list:
    all_items = []
    if paths:
        for path in paths:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_items.extend(data)
            except Exception as e:
                print(f"[rank_items] Error reading {path}: {e}", file=sys.stderr)
    else:
        # Read from stdin
        try:
            data = json.load(sys.stdin)
            if isinstance(data, list):
                all_items.extend(data)
        except Exception as e:
            print(f"[rank_items] Error reading stdin: {e}", file=sys.stderr)
    return all_items


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Rank and enrich marketing items")
    parser.add_argument("files", nargs="*", help="JSON files to process (or stdin)")
    parser.add_argument("--min-score", type=int, default=0)
    args = parser.parse_args()

    raw = load_items(args.files)
    deduped = dedup(raw)
    enriched = [enrich(item) for item in deduped if item.get("title")]
    enriched = [i for i in enriched if i["marketing_score"] >= args.min_score]
    enriched.sort(key=lambda x: x["marketing_score"], reverse=True)

    print(json.dumps(enriched, ensure_ascii=False, indent=2))
    print(f"[rank_items] {len(raw)} raw → {len(deduped)} deduped → {len(enriched)} ranked", file=sys.stderr)


if __name__ == "__main__":
    main()
