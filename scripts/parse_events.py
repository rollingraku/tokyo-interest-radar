import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FILE = SCRIPT_DIR / "output" / "source_preview.json"
OUTPUT_FILE = SCRIPT_DIR / "output" / "parsed_events.json"


def parse_event(data):
    title = data.get("pageTitle", "")

    # 从标题中识别日期：2026年11月7日
    date_match = re.search(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        title
    )

    event_date = None

    if date_match:
        year, month, day = map(int, date_match.groups())
        event_date = f"{year:04d}-{month:02d}-{day:02d}"

    # 从网页标题中提取活动名称
    event_name = title.split("|")[0].strip()

    # 从标题末尾提取地点（针对当前网站）
    location = None

    if date_match:
        location = title[date_match.end():].strip() or None

    return {
        "id": "rgs-2026",
        "title": event_name,
        "category": "game",
        "description": "活动详情请查看官方网站。",
        "location": location,
        "startAt": event_date,
        "endAt": event_date,
        "applicationDeadline": None,
        "registrationStatus": "unknown",
        "officialUrl": data.get("sourceUrl", ""),
        "sourceName": "RETRO GAME SUMMIT 官方网站",
        "lastVerifiedAt": data.get("fetchedAt", "")[:10],
        "emoji": "🎮",
        "tag": "游戏展会",
        "imageUrl": data.get("imageUrl"),
        "imageSourceUrl": data.get("imageSourceUrl"),
        "imageAlt": data.get("imageAlt"),
        "imageReviewStatus": data.get("imageReviewStatus", "missing"),
        "status": "draft"
    }


def main():
    if not INPUT_FILE.exists():
        print("找不到 source_preview.json，请先运行 fetch_events.py")
        return

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    event = parse_event(data)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps([event], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("活动信息解析完成！")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    print(f"\n保存到：{OUTPUT_FILE}")
    print("注意：这条记录仍是 draft，需要核实后才能发布。")


if __name__ == "__main__":
    main()