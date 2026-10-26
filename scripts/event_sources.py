"""官方 HTML 列表适配器；只按明确的活动日期提取，不执行脚本或调用 AI。"""
import re
import unicodedata
from datetime import date
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

PARCO_URL = "https://shibuya.parco.jp/event/"
COSME_URL = "https://www.cosme.net/store/flagship/tokyo/"


class SourceEvents(list):
    """无法可靠解析的单条记录保留旧版，不阻止其余明确记录更新。"""
    def __init__(self):
        super().__init__()
        self.protected_ids = set()
        self.warnings = []


def allowed_url(value, base, hosts):
    url = urljoin(base, value or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in hosts:
        raise ValueError("官网链接或图片域名异常")
    return url


def make_event(key, entry_id, title, start, end, location, url, image, now, evidence):
    date.fromisoformat(start)
    date.fromisoformat(end)
    if end < start:
        raise ValueError("活动结束日早于开始日")
    category, emoji, tag, name = {
        "parco": ("fashion", "👗", "时尚快闪", "涩谷 PARCO 官方活动列表"),
        "cosme": ("beauty", "💄", "美妆体验", "@cosme TOKYO 官方活动"),
    }[key]
    return {
        "id": f"{key}-{entry_id}", "title": title, "category": category,
        "emoji": emoji, "tag": tag, "description": "活动内容与参与条件请查看官方详情。",
        "location": location, "startAt": start, "endAt": end, "eventDates": [],
        "applicationDeadline": None, "registrationStatus": "unknown",
        "officialUrl": url, "sourceName": name, "sourceKey": key,
        "sourceActive": True, "fetchedAt": now, "status": "sourced",
        "imageUrl": image, "imageSourceUrl": url,
        "imageAlt": title + " 官方配图",
        "imageReviewStatus": "needs_review" if image else "missing",
        "sourceEvidence": evidence,
    }


def parco_page(html, page_url, today, now):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("a[href] .c-event-entry__title")
    if not cards:
        raise ValueError("PARCO 活动卡片结构缺失，保留旧数据")
    events = []
    for heading in cards:
        card = heading.find_parent("a")
        kind = card.select_one(".c-event-entry__category")
        # 仅采集快闪，不把展览、电影、音乐活动强行归类为服装。
        if not kind or kind.get_text(strip=True) != "POPUP":
            continue
        title = heading.get_text(" ", strip=True)
        period = card.select_one(".c-event-entry__date")
        floor = card.select_one(".c-event-entry__floor")
        if not title or not period or not floor:
            raise ValueError("PARCO 快闪的日期或地点字段缺失")
        text = period.get_text(" ", strip=True)
        match = re.fullmatch(r"\s*(\d{4})\.(\d{1,2})\.(\d{1,2})\s*[-–—]\s*(\d{4})\.(\d{1,2})\.(\d{1,2})\s*", text)
        if not match:
            raise ValueError("PARCO 日期格式改变")
        parts = list(map(int, match.groups()))
        start, end = date(*parts[:3]).isoformat(), date(*parts[3:]).isoformat()
        url = allowed_url(card.get("href"), page_url, {"shibuya.parco.jp"})
        parsed = urlparse(url)
        entry_id = parse_qs(parsed.query).get("id", [""])[0]
        if parsed.path != "/event/detail/" or not entry_id.isdigit():
            raise ValueError("PARCO 活动链接格式改变")
        image_tag = card.select_one("img")
        image = allowed_url(image_tag.get("src"), page_url, {"image.parco.jp", "shibuya.parco.jp"}) if image_tag else None
        location = floor.get_text(" ", strip=True)
        if not location or any(word in location for word in ("上海", "大阪", "名古屋")):
            continue
        event = make_event("parco", entry_id, title, start, end, "涩谷 PARCO · " + location,
                           url, image, now, {"listUrl": page_url, "period": text,
                                             "location": location, "officialCategory": "POPUP"})
        if end >= today.isoformat():
            events.append(event)
    pages = set()
    for link in soup.select('a[href]'):
        parsed = urlparse(urljoin(page_url, link["href"]))
        values = parse_qs(parsed.query).get("page", [])
        if parsed.hostname == "shibuya.parco.jp" and parsed.path == "/event/" and values:
            if not values[0].isdigit():
                raise ValueError("PARCO 分页格式异常")
            pages.add(int(values[0]))
    return events, pages


def collect_parco(fetch, today, now):
    events, pending = parco_page(fetch(PARCO_URL), PARCO_URL, today, now)
    visited = {1}
    while pending - visited:
        page = min(pending - visited)
        if page > 10 or page < 1:
            raise ValueError("PARCO 分页超过安全上限，保留旧数据")
        url = PARCO_URL + f"?page={page}"
        found, more = parco_page(fetch(url), url, today, now)
        events.extend(found)
        pending.update(more)
        visited.add(page)
    return list({event["id"]: event for event in events}.values())


def cosme_links(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("li.c-postItem")
    if not cards:
        raise ValueError("@cosme TOKYO 官方列表结构缺失")
    result = {}
    for card in cards:
        kind = card.select_one(".c-blogItem__cat")
        title = card.select_one(".c-blogItem__desc")
        link = card.select_one("a[href]")
        if not kind or kind.get_text(strip=True) != "EVENT" or not title or not link:
            continue
        title_text = title.get_text(" ", strip=True)
        # 只读 TOKYO 官方门店列出的文章，不收录普通用户博客。
        if "TOKYO" not in title_text.upper():
            continue
        url = allowed_url(link["href"], COSME_URL, {"www.cosme.net"})
        match = re.fullmatch(r"/beautist/article/(\d+)", urlparse(url).path)
        if not match:
            raise ValueError("@cosme 官方活动文章链接异常")
        image_tag = card.select_one("img[src]")
        image = allowed_url(image_tag["src"], COSME_URL, {"www.cosme.net", "fitter.cosme.net"}) if image_tag else None
        result[url] = {"entry_id": match[1], "title": title_text, "url": url, "image": image}
    if len(result) > 30:
        raise ValueError("@cosme 文章数量超过上限，请检查页面结构")
    return list(result.values())


def cosme_period(text):
    text = unicodedata.normalize("NFKC", text)
    # 只匹配“開催期間”字段；绝不从文章发布日期或预约日期推导举办时间。
    pattern = re.compile(
        r"(?:開催期間|開催日程|開催日時)\s*[:：]?\s*"
        r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*(?:\([^)]*\))?\s*[~〜～－–—-]\s*"
        r"(?:(\d{4})年\s*)?(?:(\d{1,2})月\s*)?(\d{1,2})日"
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    periods = set()
    for match in matches:
        y, m, d, ey, em, ed = match.groups()
        start = date(int(y), int(m), int(d))
        end = date(int(ey or y), int(em or m), int(ed))
        if end < start:
            raise ValueError("@cosme 举办期间跨年或日期冲突，需人工确认")
        periods.add((start.isoformat(), end.isoformat()))
    if len(periods) != 1:
        raise ValueError("@cosme 出现多个不同举办期间")
    return (*periods.pop(), matches[0].group())


def cosme_article(html, item, today, now):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("article.article-view")
    if not body:
        raise ValueError("@cosme 文章正文结构改变")
    text = body.get_text(" ", strip=True)
    period = cosme_period(text)
    if not period:
        return None
    start, end, evidence = period
    if end < today.isoformat():
        return None
    if not re.search(r"(?:@|＠)cosme\s*TOKYO", text, re.I):
        return None
    event = make_event("cosme", item["entry_id"], item["title"], start, end,
                       "原宿 @cosme TOKYO", item["url"], item["image"], now,
                       {"listUrl": COSME_URL, "period": evidence,
                        "location": "@cosme TOKYO（正文明确提及）"})
    if "完全予約制" in text or "事前予約" in text:
        event["registrationStatus"] = "partial_reservation"
    return event


def collect_cosme(fetch, today, now):
    items = cosme_links(fetch(COSME_URL))
    if not items:
        raise ValueError("@cosme 未发现官方活动文章，保留旧数据")
    events = SourceEvents()
    for item in items:
        html = fetch(item["url"])
        try:
            event = cosme_article(html, item, today, now)
        except ValueError as error:
            events.protected_ids.add("cosme-" + item["entry_id"])
            events.warnings.append(f"文章 {item['entry_id']}：{error}")
            continue
        if event:
            events.append(event)
        elif not cosme_period(BeautifulSoup(html, "html.parser").select_one("article.article-view").get_text(" ", strip=True)):
            events.protected_ids.add("cosme-" + item["entry_id"])
            events.warnings.append(f"文章 {item['entry_id']}：未找到明确的举办期间")
    return events
