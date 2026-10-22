# Tokyo Interest Radar

东京游戏、动漫、美妆和服装活动发现网站。React + Vite，Python 采集；当前不使用 AI API。

## 本机使用

```bash
npm ci
npm run dev
```

手动更新官网数据（项目根目录）：

```bash
.venv/bin/python -m pip install -r scripts/requirements.txt
.venv/bin/python scripts/update_events.py
```

没有虚拟环境时，先运行 `python3 -m venv .venv`。采集完成后，本地 Vite 页面会载入新数据；已经构建的网站需要重新构建部署。

## 每日更新的范围

- 来源：Sunshine City 官网公开的 `https://sunshinecity.jp/js/event.js`，它也是官方活动列表使用的数据。
- 自动发现符合兴趣分类的活动，获取标题、举办日期、会场、简介和官方配图，不自动生成中文翻译。
- 新记录标为 `sourced`，页面显示“官网自动同步”，不写入人工验证日期。报名信息未知时显示“待确认”。
- 图片由官网提供，保留来源；目前不能自动识别是否为实拍。既有游戏、美妆封面仍使用本地官方图片。
- 同一活动按官方 ID 去重，每天更新已有字段；成功抓取时不再出现或已结束的自动记录停止展示，保留历史数据。其他来源和人工审核记录不被覆盖。
- 日期缺失、URL 异常、空数据或网络失败时不覆盖原有数据；保持上次成功同步时间。
- 仅更新这个来源；不是全网搜索，也不会更新原来其他官网的活动信息。后续可以逐个增加官网适配器。

## Mac 关机后仍更新：GitHub Actions

工作流已经准备在 `.github/workflows/daily-update.yml`，**上传 GitHub 前不会执行，当前尚未启用云端任务**。

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
