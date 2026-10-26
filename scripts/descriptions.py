"""有原文依据的中文简介；未整理的新活动自动回退到官网原文摘录。"""
import json
import re
from pathlib import Path

NOTES_FILE = Path(__file__).with_name("description_notes.json")


def compact(text):
    return re.sub(r"\s+", "", text)


def source_excerpt(text, limit=180):
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line == "Information":
            break
        if len(line) < 18 or line.startswith(("※", "＊", "http", "開催期間", "営業時間")):
            continue
        if "韓国の話題のブランドを紹介する" in line or "期間ごとにブランドが入れ替わり" in line:
            continue
        lines.append(line)
    text = " ".join(lines)
    if len(text) <= limit:
        return text
    boundary = text.rfind("。", 40, limit)
    return text[:boundary + 1] if boundary >= 0 else text[:limit].rstrip() + "…"


def describe_event(event, text):
    notes = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    note = notes.get(event["id"])
    quotes = note.get("sourceQuotes", []) if note else []
    if quotes and all(compact(quote) in compact(text) for quote in quotes):
        event.update(description=note["description"], descriptionLanguage="zh-CN",
                     descriptionMethod="editorial", descriptionEvidence=quotes)
        return
    excerpt = source_excerpt(text)
    if excerpt:
        event.update(description=excerpt, descriptionLanguage="ja",
                     descriptionMethod="source_excerpt", descriptionEvidence=[excerpt.rstrip("…")])
    else:
        # 正文不可用时，至少明确这是哪个活动，不给所有卡片同一句占位文案。
        event.update(description=f"{event['title']}的期间限定活动，在{event['location']}举办。",
                     descriptionLanguage="zh-CN", descriptionMethod="title",
                     descriptionEvidence=[])
