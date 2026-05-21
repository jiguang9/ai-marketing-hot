# 营销热点评分逻辑（Scoring）

每条热点的 `marketing_score` 为 0-100 分，由五个维度加权。

---

## 评分维度

### 1. 平台影响力（0-25 分）

衡量该热点来源或涉及的平台在营销生态中的体量。

| 得分 | 条件 |
|------|------|
| 20-25 | 超级平台：Google, Meta, TikTok, Apple, Microsoft, Amazon, OpenAI, Anthropic |
| 12-18 | 中型平台：LinkedIn, YouTube, Instagram, Shopify, HubSpot, Salesforce, Adobe, Canva, Klaviyo |
| 4-10  | 细分工具 / 行业媒体 / 未知来源 |

---

### 2. 对获客 / 投放 / 搜索 / 转化的直接影响（0-30 分）

这是最重要的维度，衡量该热点是否直接影响营销团队的核心 KPI。

| 得分 | 条件 |
|------|------|
| 22-30 | 直接影响广告投放、搜索排名、转化率、ROAS、归因 |
| 12-20 | 影响内容生产、自动化效率、个性化能力 |
| 4-10  | 仅间接影响（品牌认知、研究参考、工具周边） |

**高影响关键词**：ads, advertising, SEO, search ranking, conversion, ROAS, attribution, bidding, checkout, revenue

**中影响关键词**：content, automation, personalization, recommendation, CRM, email

---

### 3. 行动窗口（0-20 分）

衡量该热点是否有明确的"现在可以做什么"的行动机会。

| 得分 | 条件 |
|------|------|
| 15-20 | 功能已上线 / Beta 可申请 / 规则已生效，立即可行动 |
| 8-14  | 变化即将到来，需提前准备 |
| 3-7   | 趋势性信息，无具体行动窗口 |

**行动信号词**：launch, release, now available, new feature, update, beta, announced, 发布, 上线, 新功能, 更新

---

### 4. 新鲜度（0-15 分）

衡量内容的时效性，越新越高分。

| 得分 | 发布时间 |
|------|---------|
| 15   | < 6 小时 |
| 12   | 6-24 小时 |
| 8    | 1-3 天 |
| 3    | > 3 天 |
| 7    | 发布时间未知 |

---

### 5. 可信度（0-10 分）

衡量来源的权威性。

| 得分 | 来源类型 |
|------|---------|
| 10   | 平台官方 blog / newsroom（Google, Meta, TikTok, LinkedIn, Shopify 等） |
| 8    | 知名行业媒体（Search Engine Land, Adweek, MarTech.org 等） |
| 5    | 一般博客 / 新闻源 |
| 3    | 未知来源 |

**官方域名列表**：blog.google, developers.google.com, about.fb.com, business.tiktok.com,
business.linkedin.com, blog.hubspot.com, shopify.com/blog, blog.adobe.com

---

## 优先级映射

| 分数区间 | 优先级 | 含义 |
|---------|--------|------|
| 80-100  | 立即关注 | 需要在当天做出响应或评估 |
| 60-79   | 本周跟进 | 在本周内安排研究或测试 |
| 40-59   | 保持观察 | 纳入信息雷达，定期回顾 |
| 0-39    | 低优先级 | 可以忽略，或留作参考 |

---

## 评分示例

**示例 1：Google 宣布 Performance Max 出价算法重大更新**
- 平台影响力：22（Google 超级平台）
- 业务影响：28（直接影响广告投放 ROAS）
- 行动窗口：18（已上线，立即可测试）
- 新鲜度：15（< 6 小时）
- 可信度：10（官方 blog）
- **总分：93 → 立即关注**

**示例 2：行业媒体发布 AI 营销工具使用趋势报告**
- 平台影响力：5（行业媒体）
- 业务影响：10（间接影响，策略参考）
- 行动窗口：5（无具体行动）
- 新鲜度：12（24 小时内）
- 可信度：8（知名媒体）
- **总分：40 → 保持观察**

---

## 调整原则

评分是辅助工具，不是绝对标准。以下情况可手动提升优先级：

- 竞争对手已公开采用某工具或策略
- 变化与当前正在运行的 campaign 直接相关
- 用户明确表示某平台是核心渠道
