# CLAUDE.md — ai-marketing-hot 项目上下文

## 项目定位

这是一个 **Agent Skill**，不是普通应用。SKILL.md 是核心文件，供 Claude Code、Codex、OpenClaw、Hermes 等 Agent 工具读取，定义触发条件、工作流程和输出规范。Python 脚本是可选的本地执行层。

## 关键架构决策

- **纯标准库**：所有 Python 脚本只使用 stdlib（urllib、threading、xml.etree、json 等），不引入 pyyaml、requests、aiohttp 等第三方库。如需新增依赖，必须说明原因。
- **Daemon 线程超时**：`fetch_sources.py` 和 `fetch_social.py` 用 `threading.Thread(daemon=True)` + Queue 实现并发，配合全局超时（默认 30s）优雅退出。不用 `ThreadPoolExecutor`（非 daemon 线程会卡住进程）。
- **营销相关性门槛**：`rank_items.py` 的 `compute_score()` 有 `MARKETING_SIGNAL_KW` 门槛——没有命中任何营销关键词的条目评分强制 ≤39（低优先级，不出现在报告中）。这是防噪声的核心机制，不要删除。
- **RSS 可用性**：`references/sources.yaml` 中 `enabled: false` 的源经过真实验证（2026-05-22）均为 404/403/HTML，不要轻易改回 true。

## 目录说明

```
SKILL.md          ← Agent 读取的核心文件，改动需谨慎
CLAUDE.md         ← 本文件，给 Claude Code 自己看
install.sh        ← 本地安装脚本，有防呆验证
agents/           ← Agent 框架兼容配置
scripts/          ← 可独立运行的 Python 脚本
references/       ← 人类可读的配置和规则文档
```

## 已知问题和限制

- **Reddit**：2023 年后未认证 API 全面 403。代码框架保留，实际需配置 OAuth 环境变量（`REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT`）才能用。无凭据时应静默跳过，不向用户展示错误。
- **HubSpot RSS**：响应慢（实测 2-3 分钟），30s 全局超时内通常被跳过。可用 `--timeout 60` 保留。
- **Shopify blog.atom**：返回 HTML 而非 XML，已在 sources.yaml 标记 disabled。
- **Google Ads Blog 原 URL**（`/products/ads/rss/`）：404，替换为 `blog.google/rss/`（Google 全站源）。

## 评分体系速查

总分 0-100，五维 + 社媒加分：

| 维度 | 满分 |
|---|---|
| 平台影响力 | 25 |
| 获客/投放/搜索/转化影响 | 30 |
| 行动窗口 | 20 |
| 新鲜度 | 15 |
| 可信度 | 10 |
| 社媒互动加分 | +20（social items 专属）|

优先级：≥80 立即关注 / 60-79 本周跟进 / 40-59 保持观察 / <40 低优先级（不展示）

## 输出规范（重要约束）

1. **不向用户展示内部状态**：不写"本地脚本缺失"、"第二层降级"、"非完整数据管线"、"API 403"、"fetch_social.py 失败"等。若某源覆盖有限，只写用户能理解的说明（如"X/Twitter 覆盖有限"）。
2. **周报 ≥10 条**：用户问"最近一周"时，除非明确要求简短，输出不得少于 10 条，不足时说明原因。
3. **主题分组**：默认按 8 类主题分组（见 SKILL.md 主题归类规则），不输出无分组列表。
4. **社媒内容标注**：social_discussion 类内容必须注明"社区反馈"或"讨论信号"，不当作已验证事实。

## 修改约束

- **不要新增无关文件**：不建 CHANGELOG、额外安装指南、示例数据文件。
- **不要重构已有脚本**：除非明确要求，bug fix 只改最小范围。
- **SKILL.md 改动须谨慎**：它决定 Agent 行为，改之前先确认影响范围。
- **references/ 文档改动**：这些是人类可读规则，改动后检查 SKILL.md 中的引用是否还对应。

## 常用测试命令

```sh
# 语法检查
python3 -m py_compile scripts/*.py

# 安装脚本语法
sh -n install.sh

# 实时数据 smoke test
python3 scripts/fetch_aihot.py --since-hours 24 --take 3 2>/dev/null
python3 scripts/fetch_sources.py --since-hours 24 --timeout 30 2>&1 | grep '^\[fetch'
python3 scripts/fetch_social.py --since-hours 72 --timeout 25 2>&1 | grep '^\[fetch'

# 完整 pipeline
python3 scripts/rank_items.py /tmp/mock.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); [print(i['marketing_score'], i['title'][:50]) for i in d[:5]]"
```
