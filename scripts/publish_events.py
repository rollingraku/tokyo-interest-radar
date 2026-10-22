import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFT_FILE = ROOT / "scripts/output/parsed_events.json"
EVENTS_FILE = ROOT / "src/data/events.json"


def load_json(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    drafts = load_json(DRAFT_FILE)
    existing = load_json(EVENTS_FILE)

    if not isinstance(drafts, list) or not isinstance(existing, list):
        print("数据格式错误：两个文件都应该是数组。")
        return

    published = {
        event["id"]: event
        for event in existing
    }

    changed = 0

    for event in drafts:
        if event.get("status") != "verified":
            print(f"跳过未审核活动：{event.get('title')}")
            continue

        event_id = event.get("id")

        if not event_id:
            print("跳过缺少 ID 的活动")
            continue

        published[event_id] = event
        changed += 1

    if changed == 0:
        print("没有经过审核的新活动，网站数据未改变。")
        return

    EVENTS_FILE.write_text(
        json.dumps(
            list(published.values()),
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(f"发布完成！本次新增或更新 {changed} 条活动。")


if __name__ == "__main__":
    main()