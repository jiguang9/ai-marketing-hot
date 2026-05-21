# 社媒论坛数据源（Social Sources）

本文件定义 `scripts/fetch_social.py` 使用的数据源及范围说明。

---

## 已实现（V1）

### Reddit（公开 JSON API）

**接入方式**：`https://www.reddit.com/r/{subreddit}/hot.json?limit=50`
**当前状态**：⚠️ 403 Blocked — Reddit 自 2023 年起封锁了未认证 API 访问。
V2 需通过 OAuth 接入（免费 Script App，每分钟 100 请求）。
**鉴权**：V1 无（因此 403），V2 需 Reddit Script OAuth
**速率限制**：OAuth 模式约 100 req/min

**监控社区**：

| 社区 | 关注重点 |
|---|---|
| r/marketing | 综合营销策略、案例讨论 |
| r/PPC | 付费广告实操、出价策略、归因 |
| r/SEO | SEO/AEO/GEO 最新动态、算法变化 |
| r/bigseo | 高质量 SEO 专业讨论 |
| r/Entrepreneur | 创始人视角、增长实验 |
| r/SaaS | B2B 营销、获客、留存 |
| r/shopify | 电商运营、广告投放、独立站 |
| r/ecommerce | 电商综合讨论 |
| r/DigitalMarketing | 数字营销工具和策略 |
| r/socialmedia | 社媒运营、平台动态 |

**过滤规则**：帖子 title + selftext 中必须包含营销相关关键词（见 `fetch_social.py` MARKETING_FILTER_KW）

---

### Hacker News（Algolia 搜索 API）

**接入方式**：`https://hn.algolia.com/api/v1/search?query={q}&tags=story&numericFilters=created_at_i>{ts}`
**鉴权**：无
**速率限制**：宽松（官方未明确）

**搜索查询词**：
- `AI marketing`
- `AI SEO`
- `Google Ads`
- `Meta Ads`
- `content marketing AI`
- `marketing automation`
- `AI UGC`

**关注重点**：早期工具争议、开发者视角、技术实现讨论、工具口碑

---

## 计划中（V2）

### X / Twitter

**当前状态**：未实现（需付费 API，基础版 $100+/月）
**替代方案**：Agent 联网时，可通过 Google 检索 `site:twitter.com OR site:x.com [关键词]` 获取公开帖子摘要

**目标查询词**：
```
AI marketing, AI SEO, GEO, AEO, Google Ads AI, Meta Ads AI,
TikTok Shop AI, ChatGPT shopping, Perplexity ads, AI UGC, AI outbound
```

**关注圈层**：
- 广告投手（ROAS、创意测试、归因讨论）
- SEO/内容营销人（AEO、GEO、AI 搜索优化）
- 独立开发者 / SaaS 创始人（工具口碑、增长实验）
- 品牌方 / 营销总监（战略判断、竞品分析）

---

### Product Hunt

**当前状态**：未实现（需 OAuth 或 GraphQL API）
**关注重点**：AI 营销工具发布、早期用户评价、功能争议
**典型类别**：Marketing, SEO Tools, Content, Social Media

---

### LinkedIn

**当前状态**：未实现（无公开 API）
**关注重点**：B2B 营销趋势、企业级 AI 采用、CMO 观点
**替代方案**：搜索引擎检索 LinkedIn 公开帖

---

### Indie Hackers / GrowthHackers

**当前状态**：未实现（无 RSS 或公开 API）
**关注重点**：增长实验、获客策略、工具评测

---

## 覆盖说明

| 来源 | V1 状态 | 类型 | 营销价值 |
|---|---|---|---|
| Reddit | ⚠️ 403 阻断 | 公开 API（V2 改 OAuth）| 实操经验、痛点、工具口碑 |
| Hacker News | ✅ 已实现 | 公开 API | 技术讨论、工具评测 |
| X / Twitter | ❌ 未实现 | 付费 API | 从业者实时观点（高价值） |
| Product Hunt | ❌ 未实现 | 需 API key | 新工具发现 |
| LinkedIn | ❌ 未实现 | 无公开 API | B2B 视角 |
| Indie Hackers | ❌ 未实现 | 无 API | 增长实验 |

---

## 数据质量注意事项

1. Reddit 和 HN 内容为匿名/半匿名用户发帖，可信度低于官方源
2. 单条高票帖不代表行业趋势，需结合多条相似讨论判断
3. 营销类帖子中存在工具推广/软广，注意识别
4. 时效性：`/hot` 端点返回的是热度排序，不完全等于时间排序
