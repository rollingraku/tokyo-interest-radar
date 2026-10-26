"""首次启用排序时，从本地 Git 记录补齐本站首次收录/内容更新时间。"""
import json
import subprocess

if __package__:
    from .event_updates import content_changed
    from .update_events import EVENTS_FILE, ROOT, write_json
else:
    from event_updates import content_changed
    from update_events import EVENTS_FILE, ROOT, write_json


def main():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True)

    history = git("log", "--reverse", "--format=%H %cI", "--", "src/data/events.json")
    seen = {}
    for line in history.splitlines():
        commit, observed_at = line.split(" ", 1)
        rows = json.loads(git("show", f"{commit}:src/data/events.json"))
        for row in rows:
            previous = seen.get(row["id"])
            first_seen = previous["first"] if previous else observed_at
            updated = observed_at if not previous or content_changed(previous["row"], row) else previous["updated"]
            seen[row["id"]] = {"first": first_seen, "updated": updated, "row": row}
    current = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    for row in current:
        if row["id"] in seen:
            row.setdefault("firstSeenAt", seen[row["id"]]["first"])
            row.setdefault("contentUpdatedAt", seen[row["id"]]["updated"])
    write_json(EVENTS_FILE, current)
    print(f"已按 Git 历史补齐 {len(current)} 条记录的本站更新时间。")


if __name__ == "__main__":
    main()
