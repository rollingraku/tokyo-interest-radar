"""从 Sunshine City 官方公开数据更新活动；不运行远程 JavaScript，不调用 AI。"""
import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
EVENTS_FILE = ROOT / "src/data/events.json"
FEED_URL = "https://sunshinecity.jp/js/event.js"
SOURCE_KEY = "sunshinecity"


def plain(value):
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)


def official_url(value):
    url = urljoin("https://sunshinecity.jp/", value or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "sunshinecity.jp":
        raise ValueError("来源链接必须属于 Sunshine City 官网")
    return url


def read_feed(text):
    match = re.search(r"\bvar\s+eventDatas\s*=\s*", text)
    if not match:
        raise ValueError("官方活动数据结构已改变，保留旧数据")
    rows, _ = json.JSONDecoder().raw_decode(text[match.end():].lstrip())
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("官方活动数据为空或格式错误，保留旧数据")
    return rows


def to_event(row, today, fetched_at):
    # 只收录与当前兴趣相关的官方分类，不把其他活动硬套成动漫。
    title = plain(row.get("title"))
    if not title or not row.get("eid"):
        return None
    if "グラニフ" in title or "ファッション" in title:
        category, emoji, tag = "fashion", "👗", "服装活动"
    elif 1 in row.get("categorykey", []):
        if any(word in title.upper() for word in ("TRPG", "PERSONA", "ゲーム", "メモリアル")):
            category, emoji, tag = "game", "🎮", "游戏活动"
        else:
            category, emoji, tag = "anime", "🌸", "动漫与角色"
        if "フリマ" in title:
            return None
    else:
        return None

    kind = row.get("type")
    event_dates = []
    if kind == "reg_include_date_input_type_2":
        event_dates = sorted(set(row.get("include_days", [])))
        if not event_dates:
            return None
        for value in event_dates:
            date.fromisoformat(value)
        start, end = event_dates[0], event_dates[-1]
    elif kind == "reg_include_date_input_type_1":
        start, end = row.get("startdate"), row.get("enddate")
        # 缺失结束日不擅自认定为单日活动。
        if not start or not end:
            return None
        date.fromisoformat(start)
        date.fromisoformat(end)
    else:
        return None
    if end < start:
        raise ValueError("活动日期顺序错误")
    if end < today.isoformat():
        return None
    venues = [plain(value) for value in row.get("venue", []) if value]
    if not venues:
        return None
    url = official_url(row.get("url"))
    if not re.fullmatch(r"/(?:observatory/)?event/entry-\d+\.html", urlparse(url).path):
        raise ValueError("活动详情 URL 格式异常")
    image = official_url(row["img"]) if row.get("img") else None
    return {
        "id": f"sunshine-{row['eid']}", "title": title,
        "category": category, "emoji": emoji, "tag": tag,
        "description": plain(row.get("catch_copy"))[:240] or "详情请查看官方活动页。",
        "location": "池袋 Sunshine City · " + " / ".join(venues),
        "startAt": start, "endAt": end, "eventDates": event_dates,
        "applicationDeadline": None, "registrationStatus": "unknown",
        "officialUrl": url, "sourceName": "Sunshine City 官方活动列表",
        "sourceKey": SOURCE_KEY, "sourceActive": True,
        "fetchedAt": fetched_at, "status": "sourced",
        "imageUrl": image, "imageSourceUrl": url,
        "imageAlt": plain(row.get("img_alt")) or title + " 官方配图",
        "imageReviewStatus": "needs_review" if image else "missing",
        "sourceEvidence": {"feedUrl": FEED_URL, "entryId": row["eid"],
                           "startdate": row.get("startdate"), "enddate": row.get("enddate"),
                           "include_days": row.get("include_days", []), "venue": venues},
    }


def merge_events(existing, incoming):
    # 只管理本采集器的字段；不覆盖其他来源或已人工审核的活动。
    result = {event["id"]: dict(event) for event in existing}
    current_ids = {event["id"] for event in incoming}
    for event in result.values():
        if event.get("sourceKey") == SOURCE_KEY and event.get("status") == "sourced":
            event["sourceActive"] = event["id"] in current_ids
    for event in incoming:
        previous = result.get(event["id"], {})
        if previous.get("status") == "verified":
            continue
        result[event["id"]] = {**previous, **event}
    return list(result.values())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="使用本地官方数据快照，不联网")
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    try:
        if args.input:
            text = args.input.read_text(encoding="utf-8")
        else:
            response = requests.get(FEED_URL, timeout=30, headers={"User-Agent": "TokyoInterestRadar/0.4"})
            response.raise_for_status()
            text = response.content.decode("utf-8-sig")
        rows = read_feed(text)
        incoming = []
        errors = []
        for row in rows:
            try:
                event = to_event(row, now.date(), now.isoformat())
                if event:
                    incoming.append(event)
            except (ValueError, TypeError, KeyError) as error:
                errors.append(f"{row.get('eid')}: {error}")
        # 避免格式变动或错误的半份响应覆盖正常数据。
        if errors or not incoming:
            raise ValueError("采集校验未通过，原有活动保持不变：" + "; ".join(errors or ["没有有效活动"]))
        existing = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
        merged = merge_events(existing, incoming)
        write_json(EVENTS_FILE, merged)
        write_json(ROOT / "src/data/update_status.json", {
            "lastSuccessfulAt": now.isoformat(), "sourceName": "Sunshine City 官方活动列表",
            "sourceUrl": "https://sunshinecity.jp/event/", "eventCount": len(incoming),
        })
        print(f"更新完成：{len(incoming)} 条有效活动；按 ID 去重，其他来源不变。")
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError) as error:
        print(f"更新失败：{error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
