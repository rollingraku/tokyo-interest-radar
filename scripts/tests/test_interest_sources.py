import unittest
from datetime import date

from scripts.interest_sources import dior_lips, nintendo_feed, reborn_goods, splatoon_news
from scripts.update_events import merge_events

TODAY = date(2026, 10, 26)
NOW = "2026-10-26T09:00:00+09:00"


class InterestSourceTests(unittest.TestCase):
    def test_reborn_month_precision_and_unknown_year_are_preserved(self):
        html = '''<ul class="callist"><li><h5>10月発売予定</h5><ul>
        <li><span class="title2">家庭教師ヒットマンREBORN! 缶バッジ</span>
        <span class="maker2">Maker</span><span class="price2">880円</span></li></ul></li></ul>'''
        event = reborn_goods(html, TODAY, NOW)[0]
        self.assertIsNone(event["startAt"])
        self.assertNotIn("releaseAt", event)
        self.assertIn("年份未注明", event["releaseLabel"])
        self.assertEqual(event["interestIds"], ["reborn"])
        self.assertEqual(event["priceLabel"], "880円")

    def test_official_catalog_can_have_multiple_products_at_same_url(self):
        first = {"id": "one", "sourceKey": "reborn_goods", "contentType": "product", "officialUrl": "https://example.com/catalog", "status": "sourced"}
        second = {**first, "id": "two"}
        merged = merge_events([first, second], [{**first, "priceLabel": "new"}, {**second, "priceLabel": "new"}], "reborn_goods")
        self.assertEqual([event["priceLabel"] for event in merged], ["new", "new"])

    def test_nintendo_news_date_does_not_become_release_date(self):
        xml = '''<rss><channel><item><title>スプラトゥーン3 コラボグッズ登場</title>
        <link>https://www.nintendo.com/jp/topics/article/example</link>
        <pubDate>Mon, 26 Oct 2026 09:00:00 +0900</pubDate></item>
        <item><title>別のゲームの更新</title></item></channel></rss>'''
        events = nintendo_feed(xml, TODAY, NOW)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["interestIds"], ["splatoon", "game_merch"])
        self.assertEqual(events[0]["publishedAt"], "2026-10-26")
        self.assertIsNone(events[0]["startAt"])
        self.assertNotIn("releaseAt", events[0])
        with self.assertRaises(ValueError):
            nintendo_feed("<html>error", TODAY, NOW)

    def test_splatoon_date_digits_and_old_announcements(self):
        html = '''<li class="hero_newsItem"><span class="hero_newsDate">2 0 2 6 . 6 . 1 0</span>
        <a href="https://www.nintendo.com/jp/topics/article/example">スプラトゥーン3 の情報</a></li>'''
        event = splatoon_news(html, TODAY, NOW)[0]
        self.assertEqual(event["publishedAt"], "2026-06-10")
        self.assertEqual(splatoon_news(html.replace("2 0 2 6", "2 0 2 4"), TODAY, NOW), [])

    def test_dior_only_lip_products_not_general_makeup(self):
        def product(pid, title, detail):
            return f'''<div class="product" data-pid="{pid}"><div class="product-tile__name"><a href="/ja_jp/beauty/products/{pid}">{title}</a></div>
            <div class="product-tile__short-description">{detail}</div><span class="sales">¥ 6,600</span></div>'''
        html = product("lip", "ルージュ ディオール", "リップ カラー") + product("palette", "マルチユース パレット", "アイ、リップ")
        events = dior_lips(html, TODAY, NOW)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["brand"], "Dior")
        self.assertEqual(events[0]["interestIds"], ["lipstick"])
        self.assertIsNone(events[0]["startAt"])
        self.assertIn("待确认", events[0]["releaseLabel"])


if __name__ == "__main__":
    unittest.main()
