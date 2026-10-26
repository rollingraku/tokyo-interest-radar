import unittest
from datetime import date

from scripts.event_sources import (
    COSME_URL, PARCO_URL, collect_cosme, collect_parco, cosme_article, cosme_links, cosme_period, parco_page,
)
from scripts.update_events import merge_events, update_sources

TODAY = date(2026, 10, 26)
NOW = "2026-10-26T09:00:00+09:00"


def parco_card(entry_id=1, period="2026.10.23 - 2026.11.1", kind="POPUP"):
    return f'''<a href="/event/detail/?id={entry_id}">
    <img src="https://image.parco.jp/poster.png">
    <span class="c-event-entry__category">{kind}</span>
    <span class="c-event-entry__date">{period}</span>
    <h3 class="c-event-entry__title">Fashion Brand</h3>
    <span class="c-event-entry__floor">1F GATE</span></a>'''


class OfficialSourceTests(unittest.TestCase):
    def test_parco_fields_and_category_filter(self):
        events, _ = parco_page(parco_card() + parco_card(2, kind="GALLERY"), PARCO_URL, TODAY, NOW)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], "parco-1")
        self.assertEqual(events[0]["startAt"], "2026-10-23")
        self.assertEqual(events[0]["endAt"], "2026-11-01")
        self.assertEqual(events[0]["sourceEvidence"]["officialCategory"], "POPUP")

    def test_pagination_and_duplicate_cards(self):
        pages = {
            PARCO_URL: parco_card() + '<a href="/event/?page=2">次へ</a>',
            PARCO_URL + "?page=2": parco_card() + parco_card(2),
            "https://shibuya.parco.jp/event/detail/?id=1": '<div class="event-post-edit">限定コレクションを展示するポップアップストアです。</div>',
            "https://shibuya.parco.jp/event/detail/?id=2": '<div class="event-post-edit">新作のバッグやウェアを展開する期間限定ショップです。</div>',
        }
        events = collect_parco(pages.__getitem__, TODAY, NOW)
        self.assertEqual([event["id"] for event in events], ["parco-1", "parco-2"])

    def test_changed_markup_and_bad_dates_fail(self):
        for html in ("<html>maintenance</html>", parco_card(period="2026.2.30 - 2026.11.1")):
            with self.assertRaises(ValueError):
                parco_page(html, PARCO_URL, TODAY, NOW)

    def test_expired_parco_event_is_filtered(self):
        events, _ = parco_page(parco_card(period="2026.10.1 - 2026.10.25"), PARCO_URL, TODAY, NOW)
        self.assertEqual(events, [])

    def test_cosme_uses_event_period_not_post_or_booking_date(self):
        self.assertIsNone(cosme_period("2026年10月26日投稿。予約期間：2026年10月27日～2026年11月3日"))
        period = cosme_period("開催期間：2026年10月28日（水）～2026年11月3日（火）")
        self.assertEqual(period[:2], ("2026-10-28", "2026-11-03"))
        self.assertEqual(cosme_period("開催期間:2026年10月28日~30日")[:2], ("2026-10-28", "2026-10-30"))
        with self.assertRaises(ValueError):
            cosme_period("開催期間:2026年12月28日~1月3日")
        with self.assertRaises(ValueError):
            cosme_period("開催期間:2026年10月28日~30日 開催期間:2026年11月1日~3日")

    def test_cosme_official_list_deduplicates_and_ignores_other_posts(self):
        card = '''<li class="c-postItem"><a href="https://www.cosme.net/beautist/article/123">
        <span class="c-blogItem__cat">EVENT</span><h3 class="c-blogItem__desc">【@TOKYO】FAS</h3>
        <img src="/poster.png"></a></li>'''
        items = cosme_links(card + card + card.replace("EVENT", "NEWS"))
        self.assertEqual(len(items), 1)
        event = cosme_article('''<article class="article-view">@cosme TOKYO
        開催期間：2026年10月28日～2026年11月3日 完全予約制</article>''', items[0], TODAY, NOW)
        self.assertEqual(event["category"], "beauty")
        self.assertEqual(event["registrationStatus"], "partial_reservation")
        self.assertEqual(event["sourceEvidence"]["listUrl"], COSME_URL)

    def test_source_failure_preserves_old_data_and_allows_other_updates(self):
        old = {"id": "cosme-old", "sourceKey": "cosme", "status": "sourced", "sourceActive": True}
        event = parco_page(parco_card(), PARCO_URL, TODAY, NOW)[0][0]
        def fail():
            raise ValueError("upstream changed")
        merged, report = update_sources([old], {}, {"parco": lambda: [event], "cosme": fail}, NOW)
        self.assertTrue(merged[0]["sourceActive"])
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["sources"]["cosme"]["status"], "failed")
        self.assertEqual(len(merged), 2)

    def test_merge_avoids_same_url_and_does_not_disable_other_sources(self):
        event = parco_page(parco_card(), PARCO_URL, TODAY, NOW)[0][0]
        manual = {**event, "id": "manual", "status": "verified"}
        other = {"id": "sunshine-1", "status": "sourced", "sourceKey": "sunshinecity", "sourceActive": True}
        merged = merge_events([manual, other], [event], "parco")
        self.assertEqual(len(merged), 2)
        self.assertTrue(merged[1]["sourceActive"])

    def test_ambiguous_cosme_article_preserves_previous_record(self):
        listing = '''<li class="c-postItem"><a href="https://www.cosme.net/beautist/article/123">
        <span class="c-blogItem__cat">EVENT</span><h3 class="c-blogItem__desc">【@TOKYO】Brand</h3>
        </a></li>'''
        pages = {COSME_URL: listing, "https://www.cosme.net/beautist/article/123":
                 '''<article class="article-view">@cosme TOKYO
                 開催期間:2026年10月28日~30日 開催期間:2026年11月1日~3日</article>'''}
        incoming = collect_cosme(pages.__getitem__, TODAY, NOW)
        self.assertEqual(incoming, [])
        self.assertEqual(len(incoming.warnings), 1)
        old = {"id": "cosme-123", "sourceKey": "cosme", "status": "sourced", "sourceActive": True}
        self.assertTrue(merge_events([old], incoming, "cosme")[0]["sourceActive"])

    def test_all_sources_fail_does_not_advance_success_timestamp(self):
        def fail():
            raise ValueError("offline")
        previous = {"lastSuccessfulAt": "2026-10-25T09:00:00+09:00"}
        old = [{"id": "manual", "status": "verified"}]
        merged, report = update_sources(old, previous, {"parco": fail, "cosme": fail}, NOW)
        self.assertEqual(merged, old)
        self.assertEqual(report["lastSuccessfulAt"], previous["lastSuccessfulAt"])
        self.assertEqual(report["status"], "failed")


if __name__ == "__main__":
    unittest.main()
