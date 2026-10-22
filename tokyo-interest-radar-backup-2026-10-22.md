# Tokyo Interest Radar — 开发与上线备份记录

> 整理日期：2026-10-22（东京时间）  
> 用途：保存本轮开发结果、上线配置、操作方法和下一步目标，供自己恢复项目或交接给后续开发助手。  
> 证据范围：代码和本地 Git 状态已检查；GitHub 已公开及部署成功由用户在会话中确认。本记录未独立查询云端设置，也未验证下一次定时执行。

## 1. 项目现在是什么

Tokyo Interest Radar 是一个发现东京兴趣活动的网站，关注游戏、动漫、美妆和服装活动。

- 前端：React + Vite，JavaScript。
- 采集：Python 3.13、requests、BeautifulSoup。
- 数据保存：项目中的 JSON 文件，没有数据库。
- 托管：GitHub Pages。
- 每日更新：GitHub Actions 云端运行 Python，再构建和部署前端。
- 当前不接入 AI，不需要任何 AI API Key，也不产生 AI 调用费用。
- 协作偏好：用简体中文解释，直接修改文件，小步迭代，每个功能阶段做相应验证；不要一次性重构。

## 2. 仓库、网站与上线状态

| 项目 | 地址或状态 |
| --- | --- |
| GitHub 仓库 | https://github.com/rollingraku/tokyo-interest-radar |
| Git 远端 | https://github.com/rollingraku/tokyo-interest-radar.git |
| 网站地址 | https://rollingraku.github.io/tokyo-interest-radar/ |
| Actions | https://github.com/rollingraku/tokyo-interest-radar/actions |
| Pages 设置 | https://github.com/rollingraku/tokyo-interest-radar/settings/pages |
| 默认分支 | main |
| 仓库可见性 | 用户已确认改成 Public，源码和提交历史公开 |
| 部署状态 | 用户已确认 deploy 完成；未在本轮文档整理中重新验证线上页面 |

网站公开后，其他人可以直接访问，不需要 GitHub 账号。收藏使用各自浏览器的 localStorage，目前没有账号系统，不会跨浏览器或设备同步。

## 3. 已完成的功能

### 前端

- 活动卡片、游戏/动漫/美妆/服装分类筛选。
- 搜索标题、简介、地点和标签。
- 收藏与“我的收藏”视图；初始化时过滤无效收藏 ID。
- 响应式布局：桌面三列、平板两列、手机单列。
- 卡片日期标签、详情区、官网按钮、图片来源链接。
- 官方图片加载失败时回退为活动名称文字封面。
- 图片完整展示，避免裁掉海报文字；增加键盘焦点和减少动画设置支持。
- 页面展示最近一次 Sunshine City 成功同步时间，使用东京时区。
- 支持非连续举办日，不能把分开的日期误写为连续举办。
- `vite.config.js` 使用 `base: './'`，本地图片使用 Vite 的 BASE_URL，适配 Pages 项目子路径。

### 数据与封面

- 本地数据快照共有 14 条活动：原有 4 条 `verified`，新增 10 条 `sourced`。
- 游戏 RETRO GAME SUMMIT、美妆 Tokyo Beauty Week 2026 使用已下载的官方图片，位于 `public/images/events/`。
- 原有动漫、服装活动未取得可用对应封面，保留文字封面。
- 新增的 10 条自动同步活动使用 Sunshine City 官网提供的配图地址，保留来源。
- 用户图片偏好：优先官方海报、插画、活动 Logo，尽量避免实拍。
- 当前程序无法可靠识别图片内容是否为实拍；候选和自动配图的 `imageReviewStatus` 可为 `needs_review`。前端目前不会因为该字段而隐藏配图。

### 原有单页抓取修复

`scripts/fetch_events.py` 的正文提取和 return 原先错误地落在函数外，已修正缩进。

- 输出包含非空 `pageText`；实际抓取 RETRO GAME SUMMIT 曾得到 5180 字符正文和 30 条链接。
- 先提取链接，再移除脚本、样式、导航、页脚等元素，正文最多 30000 字符。
- 自动收集分享图和正文图片候选，过滤常见社交图标、小图和重复地址。
- 优先级是启发式规则，不代表已识别图片内容。
- `parse_events.py` 会把候选封面和来源传递到草稿。

## 4. 每日更新如何工作

```text
GitHub Actions 按计划启动
  → 安装 Python 依赖并运行测试
  → update_events.py 读取 Sunshine City 官方公开数据
  → 校验、筛选、按 ID 合并活动，写入同步时间
  → npm ci 和 npm run build
  → 机器人把更新后的 JSON 提交回 main
  → 上传 dist
  → ENABLE_PAGES=true 时部署到 GitHub Pages
```

### 更新范围与规则

- 当前只有一个自动来源：Sunshine City。
- 官方列表：https://sunshinecity.jp/event/
- 官方列表使用的公开数据：https://sunshinecity.jp/js/event.js
- 使用 JSON 解码器读取 `eventDatas`，不执行远程 JavaScript。
- 获取标题、官方简介、日期、场地和配图；不自动翻译日文，不搜索整个东京。
- 仅收录适配规则选中的兴趣活动；分类目前部分依赖标题关键词。
- 同一活动使用稳定的 `sunshine-官方ID`，重复运行不会无限新增相同卡片。
- 自动记录标为 `sourced`，页面显示“官网自动同步”；这不等于人工逐字段核实。
- 缺失结束日期或场地的记录会跳过，不擅自补全；报名信息没有规则提取时保持 unknown。
- 日期格式错误、非官方链接、空数据或网络错误时退出失败，保留旧数据。
- 一次成功更新后，不再属于有效采集结果的旧自动记录设置 `sourceActive=false`，不删除历史。
- 其他来源以及 `verified` 人工记录不被该更新脚本覆盖。
- 仅本采集器管理的自动记录会因结束或消失而停止展示；原来 4 条记录没有通用过期过滤。

### 云端配置

文件：`.github/workflows/daily-update.yml`。

- 名称：`Update events and deploy`。
- 计划：`0 0 * * *`，即 UTC 00:00 / 东京时间每天 09:00。
- 也支持手动 Run workflow，以及推送到 main 后运行。
- Mac 关机不影响云端运行；GitHub 调度可能延迟，不保证准点。
- Pages 必须选择 GitHub Actions 作为部署来源。
- 仓库 Actions 变量 `ENABLE_PAGES` 必须等于字符串 `true`，否则跳过 deploy。
- 更新 job 有 contents:write，部署 job 有 pages:write 和 id-token:write；使用自动提供的 GITHUB_TOKEN，不需要在源码里保存令牌。
- 一次首次部署成功不代表定时触发已验证；应检查下一次计划运行的 Actions 记录和页面同步时间。
- 公开仓库长期无活动时定时任务可能停用；GitHub 规则以官方文档和后台为准。

## 5. 关键文件

| 文件 | 用途 |
| --- | --- |
| `src/App.jsx` | 页面、筛选、搜索、收藏和封面 |
| `src/App.css` | 卡片与响应式样式 |
| `src/data/events.json` | 网站活动数据 |
| `src/data/update_status.json` | 最近成功同步时间与来源统计 |
| `public/images/events/` | 本地官方封面 |
| `scripts/update_events.py` | 当前每日活动发现和更新入口 |
| `scripts/requirements.txt` | Python 依赖 |
| `scripts/fetch_events.py` | 旧流程：单页正文及封面候选采集 |
| `scripts/parse_events.py` | 旧流程：标题解析成 draft |
| `scripts/publish_events.py` | 旧流程：合并 verified 记录 |
| `scripts/tests/` | 采集和合并规则测试 |
| `.github/workflows/daily-update.yml` | 云端定时更新、构建、部署 |
| `.gitignore` | 排除依赖、虚拟环境、缓存和 .env |
| `README.md` | 运行与云端配置说明；其中“尚未启用”是上线前旧描述，以本备份中的用户确认状态和实际云端为准 |
| `tokyo-interest-radar-handoff.md` | 更早的交接记录，包含 AI 方案；当前决定暂缓 AI，不能把旧计划当成现状 |

## 6. 本机常用命令

以下均在项目根目录执行。

```bash
# 恢复 Node 依赖并启动本地网站
npm ci
npm run dev

# 新电脑重建 Python 环境
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt

# 手动采集当前自动来源
.venv/bin/python scripts/update_events.py

# 验证
.venv/bin/python -m unittest discover -s scripts/tests -v
npm run build
```

旧流程可以单独运行 `fetch_events.py`、`parse_events.py`，但不要在没有核实的情况下把 draft 改成 verified。`publish_events.py` 不是当前每日自动更新的入口。

本轮代码阶段曾通过 9 项测试、真实联网更新和 Vite 构建；浏览器自动化连接曾超时，不能据此声称完成了桌面和手机截图验证。此次新增文档不需要重复运行功能测试。

## 7. 修改代码后的发布习惯

云端机器人也会往 main 写入数据，因此每次开始新开发前，先查看工作区是否干净，再同步远端：

```bash
git status
git pull --ff-only
```

若有本地未提交修改，先处理修改再拉取；遇到冲突不要强推或重置覆盖。

完成修改并验证后，选择需要的文件提交，然后推送：

```bash
git add <本次修改的文件>
git commit -m "描述本次修改"
git push
```

在 Actions 查看 update 和 deploy 是否都成功。构建成功、推送成功和网站部署成功是不同阶段，不能混为一谈。

## 8. 已遇到的问题与处理方式

| 现象 | 原因或处理 |
| --- | --- |
| Mac 没有 Git / xcode-select 报错 | 安装 Command Line Tools；用户已完成，Git 2.50.1 可用 |
| VS Code 仍提示下载 Git | Reload Window，必要时完全退出再打开 |
| `Author identity unknown` | 配置 Git user.name 和 user.email，再重新提交；隐私邮箱可从 GitHub 设置复制，不编造地址 |
| GitHub 提示密码认证不支持 | HTTPS Git 不接受账号密码；用户已通过认证并上传成功。优先 VS Code 浏览器登录，不在聊天粘贴令牌 |
| Pages 提示升级 | GitHub Free 的免费 Pages 使用公开仓库；用户已确认改为 Public |
| `localhost` 连接失败 | 确认 npm run dev 正在运行，以实际端口为准 |
| 抓取失败 | 查看 Actions 或终端日志，检查源站和页面格式；不把失败运行当作更新成功 |
| 线上没有最新改动 | 检查 push、Actions、ENABLE_PAGES 和 deploy 是否成功，再刷新页面 |

## 9. 已知限制与后续方向

当前不要误认为已经完成：

- 没有 AI 审核、自动翻译、账号系统、跨设备收藏或通知。
- 没有全网发现；只增加了一个来源适配器。
- 没有统一的“即将开始 / 正在举办 / 已结束”视图或“本周末”筛选。
- 没有“今日新增 / 信息有更新”标签，目前 fetchedAt 主要是抓取时间。
- 自动封面选择无法可靠排除实拍，部分来源可能失效或防抓取。
- 原来 4 条 verified 的历史数据并不因此获得新的独立官网核实，仍需逐字段复核。
- 旧 parse_events.py 把 fetchedAt 日期写入 lastVerifiedAt，语义仍待改进。
- 旧 publish_events.py 同 ID 整条覆盖，仍有丢失字段风险；本轮没有顺手重构。

建议按小步迭代推进：

1. 检查下一次云端定时更新，确认网站同步时间变化。
2. 增加活动状态和本周末筛选，优先展示还来得及参加的活动。
3. 再逐个扩展可靠官网来源，平衡游戏、动漫、美妆和服装内容。
4. 保存 firstSeenAt、内容变更时间或内容摘要，做“新发现 / 有更新”。
5. 信息可靠后再做报名截止提醒、日历导出等功能；AI 不是当前前置条件。

## 10. 备份与恢复边界

这份文件是项目记录，不包含全部源码和图片，也不会自动备份浏览器收藏。

- 把本文件提交并推送到 GitHub 后，云端才有这份文档备份；仅创建本地文件不代表已推送。
- 另可在仓库 Code → Download ZIP 下载当前源码备份；不要把虚拟环境当成唯一可恢复的运行环境。
- 换电脑时克隆仓库、重装依赖即可恢复开发；GitHub Pages 配置和 Actions 变量属于仓库设置，不在源码 ZIP 内。
- 不保存密码、API Key、GitHub Token；`.env`、`.venv/`、`node_modules/` 不应提交。
- 本文件只记录项目公开信息与技术状态，不收录用户认证邮箱或凭证。

## 11. 给下一次开发助手的起始指令

> 请先阅读项目根目录的 `tokyo-interest-radar-backup-2026-10-22.md`，再检查实际代码和 Git 状态。项目已由用户确认上传公开 GitHub 仓库并完成 Pages 部署。当前不接入 AI；每日更新只覆盖 Sunshine City。不要把历史 verified 状态当成新近核实的证据。请用简体中文、小步修改和适量测试推进；优先活动状态、本周末筛选，再扩展官网来源。不要暴露密钥、覆盖用户修改、强推仓库或擅自改动服务器。
