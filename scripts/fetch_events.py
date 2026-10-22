import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# 第一个测试网站：RETRO GAME SUMMIT
SOURCE_URL = "https://www.retrogamesummit.com/"

# 当前脚本所在目录
SCRIPT_DIR = Path(__file__).resolve().parent

# 采集结果保存位置
OUTPUT_FILE = SCRIPT_DIR / "output" / "source_preview.json"


def fetch_page(url):
    print(f"正在访问：{url}")

    response = requests.get(
        url,
        headers={
            "User-Agent": "TokyoInterestRadar/0.3 (personal learning project)"
        },
        timeout=15,
    )

    response.raise_for_status()
    return response.text


def extract_cover_images(soup, source_url):
    """收集官方页面提供的图片；排序只是启发式，不代表已识别图片内容。"""
    candidates = []
    seen = set()

    def add(value, alt, kind):
        if not value:
            return
        url = urljoin(source_url, value.strip())
        if urlparse(url).scheme not in ("http", "https") or url in seen:
            return
        seen.add(url)
        candidates.append({
            "url": url,
            "alt": alt,
            "kind": kind,
            "sourceUrl": source_url,
        })

    for selector in ('meta[property="og:image"]', 'meta[name="twitter:image"]'):
        for meta in soup.select(selector):
            add(meta.get("content"), "", "share")

    root = soup.select_one("main") or soup.body or soup
    preferred, other = [], []
    for img in root.select("img"):
        if img.find_parent(["nav", "footer", "header"]):
            continue
        value = img.get("data-src") or img.get("data-original") or img.get("src")
        if not value:
            continue
        alt = img.get("alt", "")
        hint = (value + " " + alt).lower()
        if any(word in hint for word in (
            "icon", "spacer", "tracking", "qrcode", "qr-code", "sns_",
            "instagram", "twitter", "facebook", "youtube",
        )):
            continue
        try:
            if any(float(img.get(dim, 999)) < 80 for dim in ("width", "height")):
                continue
        except (TypeError, ValueError):
            pass
        kind = "artwork" if any(word in hint for word in (
            "poster", "visual", "keyvisual", "logo", "illustration", "kv_", "kv.",
            "海报", "插画", "ロゴ", "ビジュアル",
        )) else "unknown"
        (preferred if kind == "artwork" else other).append((value, alt, kind))

    for value, alt, kind in preferred + other:
        add(value, alt, kind)
    return candidates[:20]


def extract_information(html, source_url):
    soup = BeautifulSoup(html, "html.parser")

    # 在清理 DOM 前提取封面候选，保留来源。
    images = extract_cover_images(soup, source_url)

    # 提取网页标题
    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else "未找到网页标题"
    )

    # 提取网页中的链接
    links = []
    seen = set()

    for a in soup.select("a[href]"):
        text = a.get_text(" ", strip=True)
        url = urljoin(source_url, a["href"])

        # 只保留 HTTP/HTTPS 链接
        if urlparse(url).scheme not in ("http", "https"):
            continue

        if not text or url in seen:
            continue

        seen.add(url)

        links.append({
            "text": text[:120],
            "url": url
        })

    # 删除不需要交给 AI 的网页元素
    for element in soup.select(
        "script, style, noscript, svg, nav, footer"
    ):
        element.decompose()

    # 提取可见正文
    main = soup.select_one("main") or soup.body or soup

    page_text = main.get_text(
        separator="\n",
        strip=True
    )

    # 清理多余空行
    lines = [
        line.strip()
        for line in page_text.splitlines()
        if line.strip()
    ]

    page_text = "\n".join(lines)

    return {
        "sourceUrl": source_url,
        "pageTitle": title,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "pageText": page_text[:30000],
        "imageUrl": images[0]["url"] if images else None,
        "imageSourceUrl": source_url if images else None,
        "imageAlt": images[0]["alt"] or title if images else None,
        "imageReviewStatus": "needs_review" if images else "missing",
        "imageCandidates": images,
        "links": links[:30]
    }


def main():
    try:
        html = fetch_page(SOURCE_URL)

        data = extract_information(html, SOURCE_URL)

        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        OUTPUT_FILE.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        print("采集完成！")
        print(f"网页标题：{data['pageTitle']}")
        print(f"正文长度：{len(data['pageText'])} 字符")
        print(f"封面候选：{len(data['imageCandidates'])} 张（优先非实拍，待确认）")
        print(f"找到链接：{len(data['links'])} 条")
        print(f"保存位置：{OUTPUT_FILE}")

    except requests.RequestException as error:
        print(f"网页访问失败：{error}")
    except OSError as error:
        print(f"文件保存失败：{error}")


if __name__ == "__main__":
    main()