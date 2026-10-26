# Tokyo Interest Radar — 2026-10-26 来源扩展记录

本文件补充 2026-10-22 的备份，旧备份是当时的历史状态。

## 本次确认与修改

- 检查 GitHub 公开 API：10 月 23～26 日的 schedule 运行中，update、deploy 均成功；10 月 26 日的线上静态资源包含 11:29 的同步时间。计划 09:00，实际调度有延迟。
- 同步本地落后的 5 次云端数据提交后再开始修改，没有覆盖云端更新。
- 自动来源扩展为 Sunshine City、涩谷 PARCO、@cosme TOKYO。
- 新适配器 `scripts/event_sources.py`，每日入口仍为 `scripts/update_events.py`，无需额外 API Key。
- PARCO 解析 POPUP 列表并遍历分页；校验日期、楼层和链接，不收录一般电影、音乐和展览。
- @cosme 从官方门店页发现文章，只识别正文明确的举办期间。文章日期和预约日期不代替举办日期。
- 日期歧义的文章单独跳过并保留其已有记录；整体来源失败时保留该来源旧数据，其他来源继续；全部失败不写入新数据。
- 合并按来源隔离，以 ID 和官方详情 URL 防止重复，不覆盖人工 verified 记录。
- 页面同步说明改为多来源，显示各来源数量、失败或待确认提示，每张卡片注明来源。

## 当前数据快照

实际联网试跑三个来源成功：Sunshine City 10 条、PARCO 11 条、美妆 5 条，加原有 4 条记录共 30 张可见卡片。数量不是固定配额，取决于当天官网内容。一篇美妆文章包含不同期间，保守跳过。

## 使用与发布

```bash
.venv/bin/python scripts/update_events.py
.venv/bin/python -m unittest discover -s scripts/tests -v
npm run build
```

GitHub Actions 定时入口和 Pages 配置不变。需将本次代码提交到 main 并确认部署成功，新来源才会在网站生效。若云端又产生自动数据提交，先同步处理，不要 force push。

## 保留的限制

- 三个指定来源，不是全网发现；游戏和动漫仍主要来自 Sunshine City，后续可单独增加官网。
- 不翻译日文，不使用 AI，不自动识别配图是否为实拍。
- POPUP 列表分类并不保证都是服装商品，页面通过“时尚快闪”标签和官网链接提供上下文。
- 新记录仅为 sourced，不代表人工核实；原有四条历史 verified 数据仍需独立复核。
- 当前未新增活动状态筛选、本周末筛选、更新通知或跨设备收藏。
