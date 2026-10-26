import json
import unittest
from unittest.mock import patch

from scripts.descriptions import describe_event, source_excerpt


class DescriptionTests(unittest.TestCase):
    def event(self):
        return {"id": "example", "title": "Brand", "location": "涩谷 PARCO"}

    def test_chinese_note_requires_all_source_quotes(self):
        note = {"example": {"description": "中文活动简介。", "sourceQuotes": ["限定コレクション", "展示販売"]}}
        with patch("scripts.descriptions.NOTES_FILE") as path:
            path.read_text.return_value = json.dumps(note)
            event = self.event()
            describe_event(event, "限定コレクションの展示販売を行う期間限定ショップです。")
            self.assertEqual(event["description"], "中文活动简介。")
            self.assertEqual(event["descriptionMethod"], "editorial")
            describe_event(event, "新作バッグを紹介する期間限定のポップアップストアです。")
            self.assertEqual(event["descriptionLanguage"], "ja")
            self.assertNotEqual(event["description"], "中文活动简介。")

    def test_excerpt_skips_navigation_and_keeps_content(self):
        text = "TOKYO\n開催期間：2026年10月28日から11月3日\n新作の香りを自由に試せるポップアップイベントです。\nInformation\n住所などの共通フッター情報がここに並びます。"
        excerpt = source_excerpt(text)
        self.assertIn("新作の香り", excerpt)
        self.assertNotIn("共通フッター", excerpt)
        self.assertLessEqual(len(source_excerpt("長" * 500)), 181)

    def test_no_body_uses_specific_event_title(self):
        event = self.event()
        describe_event(event, "")
        self.assertIn("Brand", event["description"])
        self.assertIn("涩谷 PARCO", event["description"])
        self.assertEqual(event["descriptionMethod"], "title")


if __name__ == "__main__":
    unittest.main()
