"""从多个官方来源更新活动；不运行远程 JavaScript，不调用 AI。"""
import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

if __package__:
    from .event_sources import collect_cosme, collect_parco
else:
    from event_sources import collect_cosme, collect_parco

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


def merge_events(existing, incoming, source_key=SOURCE_KEY):
    # 只管理本采集器的字段；不覆盖其他来源或已人工审核的活动。
    result = {event["id"]: dict(event) for event in existing}
    current_ids = {event["id"] for event in incoming}
    for event in result.values():
        if event.get("sourceKey") == source_key and event.get("status") == "sourced":
            if event["id"] not in getattr(incoming, "protected_ids", set()):
                event["sourceActive"] = event["id"] in current_ids
    known_urls = {event.get("officialUrl"): event["id"] for event in existing if event.get("officialUrl")}
    for event in incoming:
        if event.get("sourceKey") != source_key:
            raise ValueError("采集结果来源不一致")
        if event.get("officialUrl") in known_urls and known_urls[event["officialUrl"]] != event["id"]:
            continue
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


def collect_sunshine(text, today, now):
    rows = read_feed(text)
    events = []
    for row in rows:
        event = to_event(row, today, now)
        if event:
            events.append(event)
    if not events:
        raise ValueError("Sunshine City 没有有效活动，保留旧数据")
    return events


SOURCE_INFO = {
    "sunshinecity": ("Sunshine City", "https://sunshinecity.jp/event/"),
    "parco": ("涩谷 PARCO", "https://shibuya.parco.jp/event/"),
    "cosme": ("@cosme TOKYO", "https://www.cosme.net/store/flagship/tokyo/"),
}


def update_sources(existing, previous_status, collectors, now):
    merged = existing
    previous_sources = previous_status.get("sources", {})
    reports = dict(previous_sources)
    successes = 0
    for key, collect in collectors.items():
        name, url = SOURCE_INFO[key]
        previous = previous_sources.get(key, {})
        if key == "sunshinecity" and not previous_sources:
            previous = previous_status
        report = {
            "sourceName": name, "sourceUrl": url, "lastAttemptAt": now,
            "lastSuccessfulAt": previous.get("lastSuccessfulAt"),
            "eventCount": previous.get("eventCount", 0),
        }
        try:
            incoming = collect()
            merged = merge_events(merged, incoming, key)
            report.update(status="success", lastSuccessfulAt=now, eventCount=len(incoming))
            warnings = getattr(incoming, "warnings", [])
            if warnings:
                report["warnings"] = warnings
                print(f"{name}：跳过 {len(warnings)} 篇日期不明确的文章")
            successes += 1
            print(f"{name}：{len(incoming)} 条有效活动")
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError) as error:
            report.update(status="failed", error=str(error)[:300])
            print(f"警告：{name} 更新失败，保留该来源旧数据：{error}")
        reports[key] = report
    return merged, {
        "lastSuccessfulAt": now if successes else previous_status.get("lastSuccessfulAt"),
        "lastAttemptAt": now,
        "status": "success" if successes == len(collectors) else "partial" if successes else "failed",
        "sourceName": "多个官方来源", "sources": reports,
        "successfulSourceCount": successes, "attemptedSourceCount": len(collectors),
        "eventCount": sum(event.get("status") in ("sourced", "verified")
                          and event.get("sourceActive") is not False for event in merged),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="仅使用本地 Sunshine City 数据快照，不联网")
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    status_file = ROOT / "src/data/update_status.json"
    try:
        existing = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
        previous = json.loads(status_file.read_text(encoding="utf-8")) if status_file.exists() else {}
        if args.input:
            text = args.input.read_text(encoding="utf-8")
            collectors = {"sunshinecity": lambda: collect_sunshine(text, now.date(), now.isoformat())}
        else:
            def fetch(url):
                response = requests.get(url, timeout=30, headers={"User-Agent": "TokyoInterestRadar/0.5"})
                response.raise_for_status()
                return response.content.decode("utf-8-sig")
            collectors = {
                "sunshinecity": lambda: collect_sunshine(fetch(FEED_URL), now.date(), now.isoformat()),
                "parco": lambda: collect_parco(fetch, now.date(), now.isoformat()),
                "cosme": lambda: collect_cosme(fetch, now.date(), now.isoformat()),
            }
        merged, status = update_sources(existing, previous, collectors, now.isoformat())
        if status["status"] == "failed":
            raise ValueError("所有官网更新失败，原有活动与同步时间保持不变")
        write_json(EVENTS_FILE, merged)
        write_json(status_file, status)
        print(f"更新完成：{status['successfulSourceCount']}/{status['attemptedSourceCount']} 个来源成功；当前可见 {status['eventCount']} 条活动。")
        if status["status"] == "partial":
            print("::warning::部分来源失败，其旧数据已保留，请查看页面来源状态或运行日志。")
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError) as error:
        print(f"更新失败：{error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
