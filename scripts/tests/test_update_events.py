import copy
import unittest
from datetime import date

from scripts.update_events import merge_events, read_feed, to_event


def sample():
    return {
        "eid": 123, "title": "アニメ展", "categorykey": ["", 1],
        "type": "reg_include_date_input_type_1",
        "startdate": "2026-11-01", "enddate": "2026-11-03",
        "venue": ["", "展示ホールA"],
        "url": "https://sunshinecity.jp/event/entry-123.html",
        "img": "/poster.png", "catch_copy": "<p>展示情報</p>",
    }


class UpdateTests(unittest.TestCase):
    def convert(self, row):
        return to_event(row, date(2026, 10, 22), "2026-10-22T09:00:00+09:00")

    def test_feed_is_parsed_as_json_without_execution(self):
        self.assertEqual(read_feed('var eventDatas = [{"eid": 1}]; alert(1)'), [{"eid": 1}])
        for text in ['<html>error</html>', 'var eventDatas = [];', 'var eventDatas = [alert(1)]']:
            with self.assertRaises(ValueError):
                read_feed(text)

    def test_fields_and_evidence(self):
        event = self.convert(sample())
        self.assertEqual(event["status"], "sourced")
        self.assertEqual(event["imageUrl"], "https://sunshinecity.jp/poster.png")
        self.assertEqual(event["description"], "展示情報")
        self.assertEqual(event["sourceEvidence"]["entryId"], 123)
        self.assertNotIn("lastVerifiedAt", event)

    def test_discontinuous_dates_are_preserved(self):
        row = sample()
        row.update(type="reg_include_date_input_type_2", include_days=["2026-11-03", "2026-11-01"])
        event = self.convert(row)
        self.assertEqual(event["eventDates"], ["2026-11-01", "2026-11-03"])

    def test_missing_dates_and_expired_events_are_skipped(self):
        row = sample()
        row["enddate"] = ""
        self.assertIsNone(self.convert(row))
        row.update(startdate="2026-10-01", enddate="2026-10-02")
        self.assertIsNone(self.convert(row))

    def test_bad_dates_and_untrusted_urls_fail(self):
        for changes in [{"enddate": "2026-02-30"}, {"url": "https://evil.example/event/entry-123.html"}]:
            row = sample()
            row.update(changes)
            with self.assertRaises(ValueError):
                self.convert(row)

    def test_merge_deduplicates_and_preserves_manual_records(self):
        incoming = self.convert(sample())
        manual = {"id": "manual", "status": "verified", "title": "人工数据"}
        existing = [manual, {"id": "sunshine-old", "sourceKey": "sunshinecity", "status": "sourced"}]
        original = copy.deepcopy(existing)
        merged = merge_events(existing, [incoming])
        repeated = merge_events(merged, [incoming])
        self.assertEqual(existing, original)
        self.assertEqual(len(repeated), 3)
        self.assertEqual(repeated[0], manual)
        self.assertFalse(repeated[1]["sourceActive"])
        reviewed = {**incoming, "status": "verified", "description": "人工确认内容"}
        self.assertEqual(merge_events([reviewed], [incoming])[0], reviewed)


if __name__ == "__main__":
    unittest.main()
