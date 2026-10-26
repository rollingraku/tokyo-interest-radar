"""两人的兴趣来源：保留日期精度，资讯发布日期不充当商品发售日。"""
import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests

if __package__:
    from .descriptions import describe_event
    from .reborn_images import apply_reborn_image
    from .product_series import group_reborn_series
else:
    from descriptions import describe_event
    from reborn_images import apply_reborn_image
    from product_series import group_reborn_series

JUMP_URL = "https://www.shonenjump.com/j/jumpcalendar/sakuhin/reborn/"
NINTENDO_RSS = "https://www.nintendo.com/jp/topics/c/feed/rss/"
SPLATOON_URL = "https://www.nintendo.com/jp/switch/av5ja/index.html"
DIOR_URL = "https://www.dior.com/ja_jp/beauty/page/all-new-arrivals.html"


def text(tag):
    return tag.get_text(" ", strip=True) if tag else ""


def identifier(value):
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def safe_url(value, base, hosts):
    url = urljoin(base, value)
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in hosts:
        raise ValueError("兴趣来源链接域名异常")
    return url


def item(key, title, url, now, content_type, topics, description, image=None):
    category = "anime" if key == "reborn_goods" else "beauty" if key == "dior" else "game"
    return {
        "id": key + "-" + identifier(url + title if key == "reborn_goods" else url), "title": title,
        "category": category, "contentType": content_type, "interestIds": topics,
        "description": description, "region": "日本", "location": "日本 · 线上资讯与销售渠道",
        "startAt": None, "endAt": None, "publishedAt": None,
        "releaseLabel": "发售日待公布", "registrationStatus": "unknown",
        "officialUrl": url, "sourceKey": key, "sourceActive": True,
        "sourceName": {"reborn_goods": "集英社 REBORN! 商品日历", "nintendo": "任天堂官方资讯", "dior": "Dior 日本新品页"}[key],
        "fetchedAt": now, "status": "sourced", "imageUrl": image,
        "imageSourceUrl": url, "imageAlt": title + " 官方配图",
        "emoji": {"anime": "🌸", "beauty": "💄", "game": "🎮"}[category],
        "tag": {"news": "官方资讯", "product": "新品与周边", "collab": "联名资讯"}[content_type],
    }


def reborn_goods(html, today, now):
    soup = BeautifulSoup(html, "html.parser")
    groups = soup.select(".callist > li")
    if not groups:
        raise ValueError("集英社商品日历结构改变")
    events = []
    for group in groups:
        heading = group.select_one("h5")
        if not heading:
            continue
        release = text(heading)
        exact = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", release)
        month = re.match(r"(\d{1,2})月", release)
        # 月份未注明年份时只保留原文，不擅自填成本年某一天。
        if exact:
            released = date(*map(int, exact.groups()))
            if released < today - timedelta(days=90):
                continue
        elif month and int(month[1]) < today.month:
            continue
        for row in group.select("li"):
            title = text(row.select_one(".title2"))
            if "REBORN" not in title.upper():
                continue
            price, maker = text(row.select_one(".price2")), text(row.select_one(".maker2"))
            description = f"集英社官方商品日历收录：{title}。{('厂商：' + maker + '。') if maker else ''}{('价格：' + price + '。') if price else ''}发售安排以官方标注为准。"
            event = item("reborn_goods", title, JUMP_URL, now, "product", ["reborn"], description)
            event.update(releaseLabel=release + ("（年份未注明）" if month else ""), priceLabel=price or "价格待确认")
            if exact:
                event["releaseAt"] = released.isoformat()
            event["sourceEvidence"] = {"releaseLabel": release, "title": title, "maker": maker, "price": price}
            apply_reborn_image(event)
            events.append(event)
    return group_reborn_series(events)


def nintendo_feed(xml, today, now):
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ValueError("任天堂 RSS 格式异常") from error
    nodes = root.findall("./channel/item")
    if not nodes:
        raise ValueError("任天堂 RSS 结构改变")
    events = []
    for node in nodes:
        title = node.findtext("title") or ""
        splatoon = bool(re.search(r"スプラトゥーン|splatoon", title, re.I))
        merch = bool(re.search(r"グッズ|コラボ|一番くじ|amiibo|ぬいぐるみ|オフィシャルストア", title, re.I))
        if not splatoon and not merch:
            continue
        published = parsedate_to_datetime(node.findtext("pubDate")).date()
        if published < today - timedelta(days=180) or published > today:
            continue
        url = safe_url(node.findtext("link") or "", NINTENDO_RSS, {"www.nintendo.com"})
        if not urlparse(url).path.startswith("/jp/topics/article/"):
            raise ValueError("任天堂资讯链接异常")
        topics = (["splatoon"] if splatoon else []) + (["game_merch"] if merch else [])
        description = text(BeautifulSoup(node.findtext("description") or "", "html.parser"))
        event = item("nintendo", title, url, now, "collab" if "コラボ" in title else "news", topics,
                     description[:180] or "任天堂官方公告：" + title)
        enclosure = node.find("enclosure")
        if enclosure is not None and enclosure.get("url"):
            image = enclosure.get("url")
            if urlparse(image).scheme == "https" and urlparse(image).hostname in {"www.nintendo.com", "www.nintendo.co.jp", "topics-cdn.nintendo.co.jp"}:
                event["imageUrl"] = image
        event.update(publishedAt=published.isoformat(), releaseLabel="发布日期不等于发售日")
        event["sourceEvidence"] = {"feedUrl": NINTENDO_RSS, "publishedAt": node.findtext("pubDate"), "title": title}
        events.append(event)
    return events


def splatoon_news(html, today, now):
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select(".hero_newsItem")
    if not nodes:
        raise ValueError("Splatoon 3 官方资讯结构改变")
    events = []
    for node in nodes:
        a = node.select_one('a[href*="/topics/article/"]')
        if not a:
            continue
        raw_date = re.sub(r"\s+", "", text(node.select_one(".hero_newsDate")))
        published = date.fromisoformat("-".join(f"{int(n):02d}" if i else n for i, n in enumerate(raw_date.split("."))))
        if published < today - timedelta(days=180) or published > today:
            continue
        title = text(a).removeprefix("[トピックス]")
        url = safe_url(a["href"], SPLATOON_URL, {"www.nintendo.com"})
        merch = bool(re.search(r"グッズ|コラボ|amiibo|一番くじ|キャンペーン", title, re.I))
        event = item("nintendo", title, url, now, "collab" if "コラボ" in title else "news",
                     ["splatoon"] + (["game_merch"] if merch else []), "Splatoon 官方公告：" + title)
        event.update(publishedAt=published.isoformat(), releaseLabel="发布日期不等于发售日")
        event["sourceEvidence"] = {"listUrl": SPLATOON_URL, "publishedAt": raw_date, "title": title}
        events.append(event)
    return events


def collect_nintendo(fetch, today, now):
    events = nintendo_feed(fetch(NINTENDO_RSS), today, now)
    events.extend(splatoon_news(fetch(SPLATOON_URL), today, now))
    # 初次订阅时补一篇已核对的官方周边公告；它是历史资讯，不是仍进行中的活动。
    archive_url = "https://www.nintendo.com/jp/topics/article/cc1b34ac-85a9-4549-8db5-b0f64e1ad4f2"
    try:
        soup = BeautifulSoup(fetch(archive_url), "html.parser")
        heading, published = soup.select_one("h1"), soup.select_one(".topics-articleHead__date")
        if heading and published:
            parts = list(map(int, text(published).split(".")))
            published_at = date(*parts)
            if today - timedelta(days=180) <= published_at <= today:
                title = text(heading)
                event = item("nintendo", title, archive_url, now, "collab", ["splatoon", "game_merch"],
                             "任天堂此前公布的 Splatoon 联动与周边资讯，介绍 7-Eleven 联动和 Splatoon 3 一番赏。公告中的 8 月活动已结束，当前商品库存与后续安排请以官方为准。")
                image = soup.select_one('meta[property="og:image"]')
                if image:
                    event["imageUrl"] = safe_url(image["content"], archive_url, {"assets.topics.apps-jp.nintendo.com", "www.nintendo.com"})
                event.update(publishedAt=published_at.isoformat(), historical=True, releaseLabel="历史公告 · 非进行中活动")
                event["sourceEvidence"] = {"publishedAt": text(published), "title": title, "url": archive_url}
                events.append(event)
    except (requests.RequestException, ValueError):
        print("任天堂历史周边公告暂不可用，继续同步当前 RSS 与 Splatoon 官网。")
    return list({event["officialUrl"]: event for event in events}.values())


def dior_lips(html, today, now):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".product[data-pid]")
    if not cards:
        raise ValueError("Dior 新品页结构改变")
    events = {}
    for card in cards:
        a = card.select_one(".product-tile__name a[href]")
        title = text(a)
        detail = text(card.select_one(".product-tile__short-description"))
        if not a or not (re.search(r"リップ|ルージュ|lip", title, re.I) or ("リップ カラー" in detail and not re.search(r"パレット|セット", title))):
            continue
        if re.search(r"アイ|チーク|フェイス|パウダー", title) and "リップ" not in title:
            continue
        url = safe_url(a["href"], DIOR_URL, {"www.dior.com"})
        image_tag = card.select_one("img.tile-image[src]")
        image = safe_url(image_tag["src"], DIOR_URL, {"www.dior.com"}) if image_tag else None
        price = text(card.select_one(".sales"))
        event = item("dior", title, url, now, "product", ["lipstick"],
                     f"Dior 日本官网新品与限定品栏目收录。{detail}。{('官网标价：' + price + '。') if price else ''}具体发售日未从列表确认。", image)
        event.update(brand="Dior", priceLabel=price or "价格待确认", releaseLabel="新品页收录 · 具体发售日待确认")
        event["id"] = "dior-" + card["data-pid"]
        event["sourceEvidence"] = {"listUrl": DIOR_URL, "name": title, "detail": detail, "price": price}
        describe_event(event, title + "\n" + detail)
        events.setdefault(title, event)
    return list(events.values())
