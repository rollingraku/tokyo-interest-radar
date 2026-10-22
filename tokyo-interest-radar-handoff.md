# Tokyo Interest Radar — Codex 项目交接记录

> 更新日期：2026-10-22  
> 用途：将本次 ChatGPT 会话中的项目背景、已完成内容、当前故障、下一步目标交给 VS Code 中的 Codex。  
> 注意：这是**对话总结**，不是对本地文件的实时检查；Codex 应先读取实际代码，再修改。

## 1. 项目目标

开发 **Tokyo Interest Radar**：面向东京的兴趣活动发现 Web 应用，关注游戏、动漫、美妆、时尚类活动。长期希望实现：

- 自动发现和采集活动官网信息；
- AI 提取、审核、去重，生成中文摘要；
- 按兴趣筛选、关键词搜索、收藏；
- 后续加入推荐、日历提醒和分享功能。

开发者在 Mac（Apple Silicon）上使用 VS Code，主要以中文交流，倾向**小步迭代、每步可运行验证**。目前只在本机开发；未来可能部署到家用服务器，但**不要擅自改动现有服务器环境**。

## 2. 技术栈和项目位置

- 项目路径：`~/tokyo-interest-radar`
- 前端：React + Vite（JavaScript）
- 数据：`src/data/events.json`
- 采集/解析：Python 3.13、`requests`、`beautifulsoup4`
- Python 虚拟环境：项目根目录 `.venv/`
- 本地启动：`npm run dev`；Vite 常用端口 5173，但以终端显示为准
- Python：Mac 系统终端通常使用 `python3`；激活 `.venv` 后通常可用 `python`

### 重要文件

```text
tokyo-interest-radar/
├── src/
│   ├── App.jsx
│   ├── App.css
│   ├── index.css
│   └── data/
│       └── events.json
├── scripts/
│   ├── fetch_events.py
│   ├── parse_events.py
│   ├── publish_events.py
│   └── output/
│       ├── source_preview.json
│       └── parsed_events.json
├── .venv/
└── package.json
```

`test_ai.py` 曾被建议创建，但**用户尚未确认已创建或运行成功**。

## 3. 已完成的功能

### 前端 v0.1–v0.2

- React + Vite 项目创建成功，`npm run dev` 曾正常运行。
- 活动卡片、分类筛选、关键词搜索、收藏、收藏页、响应式布局已实现。
- 收藏记录保存在 `localStorage`。
- 曾出现旧假数据的收藏 ID 导致“收藏数量 1、页面为空”的问题，已通过只保留当前有效活动 ID 解决：

```jsx
const [favorites, setFavorites] = useState(() => {
  const savedFavorites = readFavorites();
  const validIds = new Set(events.map((event) => event.id));
  return savedFavorites.filter((id) => validIds.has(id));
});
```

- `App.jsx` 从 `src/data/events.json` 导入数据，并仅显示 `status === "verified"` 的活动。
- 数据文件曾包含 4 条活动：RETRO GAME SUMMIT、TOKYO ANIME NEXT、Tokyo Beauty Week、Tommy Hilfiger × FRGMT。**注意：之前会话对这四条的“已核实”说法缺乏独立证据，不能据此认为它们真的经过官网逐字段验证。应重新核对官方来源和日期。**

### Python 采集 v0.3

用户运行 `fetch_events.py` 成功，终端曾输出：

```text
正在访问：https://www.retrogamesummit.com/
采集完成！
网页标题：RETRO GAME SUMMIT Lv.6 | 2026年11月7日 東京たま未来メッセ
找到链接：30 条
保存位置：/Users/rollingraku/tokyo-interest-radar/scripts/output/source_preview.json
```

`parse_events.py` 成功将网页标题解析为一条结构化记录，写入 `scripts/output/parsed_events.json`：

```json
{
  "id": "rgs-2026",
  "title": "RETRO GAME SUMMIT Lv.6",
  "category": "game",
  "description": "活动详情请查看官方网站。",
  "location": "東京たま未来メッセ",
  "startAt": "2026-11-07",
  "endAt": "2026-11-07",
  "applicationDeadline": null,
  "registrationStatus": "unknown",
  "officialUrl": "https://www.retrogamesummit.com/",
  "sourceName": "RETRO GAME SUMMIT 官方网站",
  "lastVerifiedAt": "2026-10-22",
  "emoji": "🎮",
  "tag": "游戏展会",
  "status": "draft"
}
```

说明：上述日期和地点**来自采集到的网页标题**，尚不能代替完整的官网审核。`lastVerifiedAt` 字段目前容易造成误解：它实际可能仅代表抓取/解析日期，建议改为 `fetchedAt`，审核通过才写入真正的验证时间。

### 发布流程

`publish_events.py` 的设计：

- 读取 `scripts/output/parsed_events.json`；
- 只接受 `status === "verified"` 的记录；
- 按 ID 合并到 `src/data/events.json`；
- 跳过 `draft`；
- 已有相同 ID 时会**整条覆盖**，存在丢失已有字段的风险。

用户曾遇到“修改 status 后仍提示未审核”，排查重点包括：是否保存了正确文件、是否又运行 `parse_events.py` 将 `status` 重置为 `draft`。随后用户反馈“搞定了”，说明当时发布流程已能工作。

### 本地环境问题

- `ERR_CONNECTION_REFUSED (-102)` 访问 `http://localhost:5173/`：因为 Vite 开发服务器未运行，重新执行 `npm run dev` 即可；实际端口以终端输出为准。
- `zsh: command not found: python`：Mac 终端可使用 `python3`，或者先运行 `source .venv/bin/activate`。

## 4. 当前阻塞问题：抓取结果没有 `pageText`

为了给 AI 提供活动官网正文，之前建议修改 `scripts/fetch_events.py` 的 `extract_information()`，在返回 JSON 时加入 `pageText`。建议代码逻辑：

```python
# 注意：应在提取链接之后再修改 soup，避免误删链接
for element in soup.select("script, style, noscript, svg, nav, footer"):
    element.decompose()

main = soup.select_one("main") or soup.body or soup
page_text = main.get_text(separator="\n", strip=True)
lines = [line.strip() for line in page_text.splitlines() if line.strip()]
page_text = "\n".join(lines)

return {
    "sourceUrl": source_url,
    "pageTitle": title,
    "fetchedAt": datetime.now(timezone.utc).isoformat(),
    "pageText": page_text[:30000],
    "links": links[:30],
}
```

**最新实际检查结果**（用户在终端运行）：

```text
字段： ['sourceUrl', 'pageTitle', 'fetchedAt', 'links']
正文长度： 0
正文预览：
```

这说明**现有 `source_preview.json` 里还没有 `pageText` 字段**；不代表官网正文真的为空。可能是 `fetch_events.py` 尚未正确修改/保存，或修改后尚未重新运行。

Codex 应首先：

1. 查看本地 `scripts/fetch_events.py`，确定 `pageText` 提取代码是否实际存在、缩进和 `return` 是否正确。
2. 在原有采集功能不退化的前提下修复正文提取；建议过滤导航、脚本、样式和冗余空白，保留主要正文。
3. 运行 `python3 scripts/fetch_events.py`（如依赖缺失则激活 `.venv`），确认 `source_preview.json` 包含**非空** `pageText`。
4. 如官网为 JavaScript 动态渲染，需明确告知，不要假装抓取成功；先考虑是否有静态 HTML、JSON-LD 或官方公开数据源。

检查命令：

```bash
python3 -c "import json; d=json.load(open('scripts/output/source_preview.json')); print('字段：',list(d.keys())); print('正文长度：',len(d.get('pageText',''))); print('正文预览：',d.get('pageText','')[:300])"
```

## 5. 当前明确目标：v0.4 使用 AI API 自动审核

用户**明确选择方案 B：通过 AI API 自动审核**，而不是手动将内容复制给 ChatGPT。目标：

```text
官方网页
  ↓ Python 采集正文及来源
AI API 提取结构化活动数据 + 原文证据
  ↓
Python 校验格式、日期、URL、证据、重复记录
  ↓
合格 → 发布；证据不足 → 待审核，不发布
  ↓
React 网站显示
```

### 建议实现顺序

1. **先修复 `pageText`**，确保 AI 有真实的输入材料。
2. 选择当前可用、低成本、支持结构化输出的 OpenAI API 模型；**不要照搬之前会话建议的 `gpt-6-luna`，该模型 ID 未经过验证**。以用户 API 账户实际可用模型和官方文档为准。
3. 在 Python 虚拟环境中安装 `openai`，从环境变量 `OPENAI_API_KEY` 读取密钥；不写入源码，不提交 Git。建议使用 `.env` 时必须加入 `.gitignore`。
4. 实现单条活动 AI 审核，输出例如 `scripts/output/ai_review_result.json`，包含结构化字段、原文证据、缺失项、审核决定和原因。
5. **严格区分 AI 判断与客观核实**：AI 不能仅凭自我评分批准活动；必要字段应有可定位的官网原文证据，Python 验证字段格式、合理性与来源。对有冲突或证据不足的记录保留 `draft`/`needs_review`。
6. 第一版只处理 **1 个官网**、输入长度限制约 **12,000 字符**、默认**不自动发布**、不自动重试；先检查结果和 token 用量，再决定自动发布策略。
7. 审核通过后才调用发布脚本，且改进合并逻辑，避免以 `unknown`/`null` 覆盖已确认的信息。

### API 配置

用户之前收到的建议：

```bash
cd ~/tokyo-interest-radar
source .venv/bin/activate
python -m pip install --upgrade openai
export OPENAI_API_KEY="<用户自己的密钥>"
```

**尚未确认用户已经创建 API Key、安装 SDK 或成功连接。** Codex 应先检查环境变量是否存在（只报告存在与否，**不要打印密钥**），再提供下一步。

- OpenAI API 与 ChatGPT Plus **独立计费**。
- 建议先检查 API 计费设置，配置预算提醒，并在代码中限制请求次数、输入长度、输出 token 数量、重试次数和模型。
- 之前会话给出的特定模型价格和引用未在本交接中独立核验，不应当作准确报价。

## 6. 开发协作要求

- 用**简体中文**解释改动。
- 优先读取并修改实际项目文件，不要只给用户长段手工复制步骤（Codex 在 VS Code 内可直接操作工作区）。
- 每次聚焦一个小目标，改动后运行相应命令验证。
- 不要暴露 API Key、私密路径或凭证；`.venv/`、`.env` 和适当的生成输出应在 `.gitignore` 中。
- 保留原有 React 功能；不随意重构无关代码。
- 不要把 AI 生成的信息未经验证直接标记为 `verified`。
- 如需访问或改动服务器，必须先征得用户同意；当前只做本地开发。

## 7. 给 Codex 的立即执行任务

**请先读取当前工作区的 `scripts/fetch_events.py`、`scripts/parse_events.py`、`scripts/publish_events.py`、`src/data/events.json` 和 `.gitignore`，并完成以下最小任务：修复 `fetch_events.py`，让 `scripts/output/source_preview.json` 确实包含非空 `pageText`；运行验证并报告结果。不要在此步直接开始自动发布，也不要修改服务器。完成后，再协助我配置 OpenAI API 和实现安全的单条活动 AI 审核。**
