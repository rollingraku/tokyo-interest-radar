# Tokyo Interest Radar

东京游戏、动漫、美妆和服装活动发现网站。React + Vite，Python 采集；当前不使用 AI API。

## 本机使用

```bash
npm ci
npm run dev
```

手动更新全部三个官网来源（项目根目录）：

```bash
.venv/bin/python -m pip install -r scripts/requirements.txt
.venv/bin/python scripts/update_events.py
```

没有虚拟环境时，先运行 `python3 -m venv .venv`。采集完成后，本地 Vite 页面会载入新数据；已经构建的网站需要重新构建部署。

## 每日更新的范围

当前每天采集三个官方来源，不使用 AI：

| 来源 | 覆盖内容 | 采集方式 |
| --- | --- | --- |
| [Sunshine City](https://sunshinecity.jp/event/) | 游戏、动漫、角色活动及部分服装活动 | 官方 `eventDatas` 数据 |
| [涩谷 PARCO](https://shibuya.parco.jp/event/) | POPUP 时尚快闪 | 官方列表及分页中的日期、楼层、配图 |
| [@cosme TOKYO](https://www.cosme.net/store/flagship/tokyo/) | 美妆品牌活动 | 官方门店列表链接的文章正文，匹配明确的“開催期間” |

- 活动使用稳定 ID 和详情 URL 去重，`sourceKey` 区分来源；原有人工记录不被覆盖。
- 自动记录为 `sourced`，显示“官网自动同步”，不自动变成 `verified`；报名信息没有证据时保留未知。
- 不把新闻发布日期当作活动日期。日期缺失、多个期间冲突的美妆文章单独跳过并记录提示，其已有记录保留。
- PARCO 当前只接入 POPUP 快闪，不把音乐、电影和一般展览硬归类为服装；后续可扩展分类。
- 一个来源失败时只保留它的旧数据，其他成功来源正常更新和部署；全部失败时退出失败，保留原有数据。
- 一次成功同步后，该来源不再有效的自动记录停止展示，历史数据保留。人工记录不受自动下架规则影响。
- 页面展示各来源状态、活动数量和每张卡片的来源；抓取时间不能代替人工核实时间。
- 官方配图保留来源，但目前不能可靠区分海报与实拍；不自动生成中文翻译。
- 仍是指定官网适配器，不是全网搜索。扩展其他官网需要确认格式后逐个接入。

## Mac 关机后仍更新：GitHub Actions

工作流位于 `.github/workflows/daily-update.yml`。项目已完成 GitHub Pages 部署；2026-10-26 已核对之前四天的定时采集与部署均成功。下面保留配置和恢复步骤。

1. 在 GitHub 创建仓库，默认分支使用 `main`，上传本项目的源码和 `.github` 目录。不要上传 `.venv`、`node_modules`、`.env` 或任何密钥，已在 `.gitignore` 排除。
2. 仓库的 Actions 页面允许工作流运行，然后选择 **Update events and deploy → Run workflow** 试跑一次。
3. 默认每天 UTC 00:00（东京时间 09:00）抓取、测试、构建，并把数据更新提交回仓库。它在 GitHub 云端执行，不依赖你的 Mac。
4. 如果还希望打开网址就看到更新后的网页，在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**；再到 **Settings → Secrets and variables → Actions → Variables** 添加 `ENABLE_PAGES`，值为 `true`，最后重新运行工作流。没有设置这个变量时只更新仓库，不发布网站。
5. 成功部署后，在工作流的 `github-pages` 环境或 Settings → Pages 查看网站网址。项目已适配 GitHub Pages 子目录资源路径。

免费方案可以用公开仓库和标准 Ubuntu runner；公开仓库会让源码和提交历史公开。私有仓库的 Actions 有免费额度，GitHub Free 的 Pages 适用于公开仓库，请按账户实际计划选择。没有部署的网站不会因为更新仓库而自动变成在线网站。

注意：GitHub 定时任务不是精准闹钟，繁忙时可能延迟；只在默认分支运行。公开仓库连续 60 天没有活动时，定时工作流可能被停用，需要在 Actions 中重新启用。分支保护禁止机器人直接提交时，需要调整为 PR 更新流程。

官方说明：[定时触发](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)、[Actions 费用](https://docs.github.com/en/billing/concepts/product-billing/github-actions)、[Pages 部署](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。

## 验证

```bash
.venv/bin/python -m unittest discover -s scripts/tests -v
npm run build
```

旧的单页抓取、解析、人工审核发布流程仍保留：`fetch_events.py` → `parse_events.py` → 人工审核 → `publish_events.py`。每日同步使用独立的 `update_events.py`，不改变旧流程。

## 2026-10-26 来源扩展

每日更新由 1 个来源扩展到 3 个。实际试跑得到 Sunshine City 10 条、PARCO 11 条、@cosme TOKYO 5 条，加上原有 4 条人工记录，当前共 30 张可见卡片（数量会随日期和官网变化）。一篇美妆文章含不同举办期间，已跳过而未猜测日期。

新增适配器在 `scripts/event_sources.py`，定时入口仍是 `scripts/update_events.py`，无需更改 Actions 计划。推送此版本并部署成功后，云端才会使用新来源；本机试跑不等于已发布。来源扩展详情见 `tokyo-interest-radar-update-2026-10-26.md`。

## 活动简介

PARCO 采集详情正文，@cosme 复用已抓取的文章正文。当前这批活动的简短中文介绍保存在 `scripts/description_notes.json`，每条带原文锚点；每天同步时只有锚点仍存在才保留中文文案。未来未整理或原文变化的新活动自动显示官网原文摘录，不调用翻译 API，也不保证所有未来活动自动生成中文。

正文不可访问时使用活动名称与地点生成简短说明，不影响该活动日期等列表信息的更新。简介仅是内容摘要，不代表整条活动已人工核实。
