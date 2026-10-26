import unittest

from scripts.event_updates import with_update_times


class EventUpdateTests(unittest.TestCase):
    def test_new_item_records_first_seen(self):
        item = with_update_times({}, {"title": "新内容"}, "2026-10-26T10:00:00+09:00")
        self.assertEqual(item["firstSeenAt"], item["contentUpdatedAt"])

    def test_routine_fetch_does_not_bump_content(self):
        old = {"title": "活动", "fetchedAt": "2026-10-25T09:00:00+09:00", "firstSeenAt": "2026-10-22T09:00:00+09:00", "contentUpdatedAt": "2026-10-24T09:00:00+09:00"}
        new = with_update_times(old, {**old, "fetchedAt": "2026-10-26T09:00:00+09:00"}, "2026-10-26T09:00:00+09:00")
        self.assertEqual(new["contentUpdatedAt"], old["contentUpdatedAt"])
        changed = with_update_times(old, {**old, "title": "活动时间调整"}, "2026-10-26T09:00:00+09:00")
        self.assertEqual(changed["firstSeenAt"], old["firstSeenAt"])
        self.assertEqual(changed["contentUpdatedAt"], "2026-10-26T09:00:00+09:00")


if __name__ == "__main__":
    unittest.main()
