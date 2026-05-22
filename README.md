# ai-marketing-hot

AI 营销热点 Skill，适用于 Claude Code、Codex、OpenClaw、Hermes 等 Agent 工具。

聚合 AI 行业动态、营销平台官方源和公开社区讨论，输出面向营销团队的中文热点简报——不是新闻搬运，每条热点必须有**营销影响**、**建议动作**和**适合谁**。

---

## 安装

从仓库根目录运行：

```sh
git clone https://github.com/jiguang9/ai-marketing-hot
cd ai-marketing-hot
sh install.sh                    # 安装到 ~/.codex/skills/ai-marketing-hot
sh install.sh ~/my/skills/path   # 或指定目录
```

安装后向 Agent 说：`帮我安装这个 skill：https://github.com/jiguang9/ai-marketing-hot`

---

## 触发方式

在任意支持此 Skill 的 Agent 中直接提问：

- 今天 AI 营销圈有什么热点？
- 最近一周 AI 广告/SEO/电商有什么变化？
- Google Ads 最近有什么值得关注的？
- AI 营销人在社区里在聊什么？
- 给我一份 AI 营销日报

---

## 数据源

| 层级 | 来源 | 状态 |
|---|---|---|
| AI 行业 | aihot.virxact.com API | ✅ 无需 key |
| 营销官方 | HubSpot、Google Blog、SEJ、Adweek、Salesforce 等 RSS | ✅ 5 个已启用 |
| 社区讨论 | Hacker News（Algolia API） | ✅ 无需 key |
| 社区讨论 | Reddit（需 OAuth 环境变量） | ⚙️ 配置后可用 |
| 社区讨论 | X/Twitter | ❌ 需付费 API |

RSS 源可用性以 `references/sources.yaml` 中 `enabled: true` 为准。

---

## Reddit OAuth 配置（可选）

```sh
export REDDIT_CLIENT_ID=your_client_id
export REDDIT_CLIENT_SECRET=your_client_secret
export REDDIT_USER_AGENT=ai-marketing-hot/1.0
```

申请地址：https://www.reddit.com/prefs/apps（选 Script 类型，免费）

---

## 目录结构

```
SKILL.md              Skill 定义、工作流程、输出规范（Agent 读取）
install.sh            本地安装脚本
agents/
  openai.yaml         Codex/OpenAI 兼容配置
scripts/
  fetch_aihot.py      拉取 AI HOT API
  fetch_sources.py    拉取营销 RSS 源（并发，30s 全局超时）
  fetch_social.py     拉取 HackerNews + Reddit
  rank_items.py       去重、分类、评分（0-100）
  build_report.py     生成中文 Markdown 简报
references/
  sources.yaml        RSS 源配置（含可用性状态）
  taxonomy.md         营销分类体系（12 个分类）
  scoring.md          评分维度说明
  social_sources.md   社媒源接入策略
  social_scoring.md   社媒互动评分规则
  output_formats.md   输出格式模板
```

---

## 手动运行 Pipeline

```sh
python scripts/fetch_aihot.py --since-hours 24 --take 100 > /tmp/aihot.json
python scripts/fetch_sources.py --since-hours 24 --timeout 30 > /tmp/sources.json
python scripts/fetch_social.py --since-hours 24 --timeout 30 > /tmp/social.json
python scripts/rank_items.py /tmp/aihot.json /tmp/sources.json /tmp/social.json --min-score 40 > /tmp/ranked.json
python scripts/build_report.py --input /tmp/ranked.json --mode daily
```

支持的输出模式：`daily` / `opportunities` / `platform` / `social`

---

## 版本

v1.2 — 见 [SKILL.md](SKILL.md) 中的 version 字段
