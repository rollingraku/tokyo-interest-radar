"""按已确认的商品系列合并角色/商品变体，不合并同一作品的不同系列。"""
import hashlib
import re


def reborn_series(title):
    if "Grand Arcanist" in title:
        return "Grand Arcanist"
    if "ぴくりあプレート" in title and "レトロファッション" in title:
        return "ぴくりあプレート hologram · レトロファッション"
    if "Grandista" in title:
        return "Grandista"
    if "るかっぷ" in title:
        return "るかっぷ"
    match = re.search(r"フェイスポーチ\s*vol\.\s*\d+", title, re.I)
    return match.group() if match else None


def group_reborn_series(items):
    groups = {}
    singles = []
    for event in items:
        series = reborn_series(event["title"])
        if not series:
            singles.append(event)
            continue
        maker = event.get("sourceEvidence", {}).get("maker", "")
        groups.setdefault((maker, series), []).append(event)
    for (maker, series), members in groups.items():
        members = sorted({event["id"]: event for event in members}.values(), key=lambda event: event["title"])
        event = dict(members[0])
        event["id"] = "reborn-series-" + hashlib.sha256((maker + "|" + series).encode()).hexdigest()[:16]
        event["title"] = "家庭教师 REBORN! · " + series + " 系列"
        event["seriesName"] = series
        event["legacyIds"] = sorted(member["id"] for member in members)
        event["variants"] = [{key: member[key] for key in ("id", "title", "priceLabel", "releaseLabel", "officialUrl", "releaseAt") if key in member} for member in members]
        releases = list(dict.fromkeys(member["releaseLabel"] for member in members))
        prices = list(dict.fromkeys(member["priceLabel"] for member in members))
        event["releaseLabel"] = releases[0] if len(releases) == 1 else "多批次发售 · 展开查看"
        dates = {member.get("releaseAt") for member in members}
        if len(dates) != 1:
            event.pop("releaseAt", None)
        event["priceLabel"] = prices[0] if len(prices) == 1 else "各款价格不同 · 展开查看"
        event["description"] = f"{series} 系列合并收录 {len(members)} 款周边，不同角色与商品款式在下方展开查看。" + (f"厂商：{maker}。" if maker else "")
        event["sourceEvidence"] = {"seriesName": series, "maker": maker, "items": [member["sourceEvidence"] for member in members]}
        singles.append(event)
    return singles
