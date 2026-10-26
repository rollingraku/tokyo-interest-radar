import unittest

from scripts.product_series import group_reborn_series
from scripts.update_events import merge_events


def product(item_id, title, price="880円", release="10月発売予定"):
    return {"id": item_id, "title": title, "priceLabel": price, "releaseLabel": release,
            "officialUrl": "https://www.shonenjump.com/j/jumpcalendar/sakuhin/reborn/",
            "sourceKey": "reborn_goods", "status": "sourced", "sourceActive": True,
            "contentType": "product", "fetchedAt": "2026-10-26T12:00:00+09:00",
            "sourceEvidence": {"maker": "amie", "title": title}}


class ProductSeriesTests(unittest.TestCase):
    def test_character_variants_collapse_and_keep_individual_details(self):
        members = [product("mukuro", "REBORN! ぴくりあプレート hologram レトロファッション 05.六道骸"),
                   product("hibari", "REBORN! ぴくりあプレート hologram レトロファッション 04.雲雀恭弥")]
        result = group_reborn_series(members)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["variants"]), 2)
        self.assertEqual(result[0]["legacyIds"], ["hibari", "mukuro"])
        self.assertEqual(result, group_reborn_series(list(reversed(members))))
        self.assertEqual(result[0]["id"], group_reborn_series(members[:1])[0]["id"])

    def test_different_series_stay_separate_and_prices_not_lost(self):
        items = [product("a", "REBORN! Grand Arcanist アクリルスタンド", "1,650円"),
                 product("b", "REBORN! Grand Arcanist 缶バッジ", "550円", "11月発売予定"),
                 product("c", "るかっぷ REBORN! 雲雀恭弥")]
        result = group_reborn_series(items)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["releaseLabel"], "多批次发售 · 展开查看")
        self.assertEqual({v["priceLabel"] for v in result[0]["variants"]}, {"1,650円", "550円"})
        self.assertNotIn("releaseAt", result[0])

    def test_daily_merge_hides_old_roles_and_keeps_one_series(self):
        members = [product("a", "るかっぷ REBORN! 沢田綱吉"), product("b", "るかっぷ REBORN! 雲雀恭弥")]
        grouped = group_reborn_series(members)
        merged = merge_events(members, grouped, "reborn_goods")
        repeated = merge_events(merged, grouped, "reborn_goods")
        active = [item for item in repeated if item.get("sourceActive")]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["legacyIds"], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
