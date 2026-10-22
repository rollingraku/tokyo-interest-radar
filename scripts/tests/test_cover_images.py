import unittest

from scripts.fetch_events import extract_information
from scripts.parse_events import parse_event


class CoverImageTests(unittest.TestCase):
    def test_share_image_and_source_survive_parsing(self):
        data = extract_information('''<title>活动</title>
            <meta property="og:image" content="/poster.png">
            <main><p>正文</p><img src="/poster.png"></main>''',
            "https://example.com/event/")
        self.assertEqual(data["imageUrl"], "https://example.com/poster.png")
        self.assertEqual(len(data["imageCandidates"]), 1)
        self.assertEqual(data["pageText"], "正文")
        event = parse_event(data)
        self.assertEqual(event["imageSourceUrl"], data["sourceUrl"])
        self.assertEqual(event["imageReviewStatus"], "needs_review")
        self.assertEqual(event["status"], "draft")

    def test_artwork_priority_and_noise_filtering(self):
        data = extract_information('''<body>
            <nav><img src="/nav.png"></nav><main>
            <img src="/photo.jpg"><img data-src="poster.png">
            <img src="/icon.png"><img src="/small.png" width="1">
            <img src="javascript:alert(1)"><img src="data:image/png,abc">
            </main></body>''', "https://example.com/event/")
        self.assertEqual(data["imageUrl"], "https://example.com/event/poster.png")
        self.assertEqual(len(data["imageCandidates"]), 2)

    def test_no_image_remains_explicit(self):
        data = extract_information("<p>正文</p>", "https://example.com/")
        self.assertIsNone(data["imageUrl"])
        self.assertEqual(data["imageReviewStatus"], "missing")
        self.assertEqual(data["imageCandidates"], [])


if __name__ == "__main__":
    unittest.main()
