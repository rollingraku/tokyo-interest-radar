import unittest

from scripts.reborn_images import apply_reborn_image


class RebornImageTests(unittest.TestCase):
    def test_fallback_is_explicitly_a_reference_not_product_photo(self):
        event = {"id": "new-reborn", "imageUrl": None}
        apply_reborn_image(event)
        self.assertTrue(event["imageUrl"].startswith("/images/reborn/"))
        self.assertEqual(event["imageKind"], "franchise_art")
        self.assertIn("不代表此商品", event["imageAlt"])
        self.assertEqual(event["imageReviewStatus"], "reference")

    def test_specific_product_image_takes_precedence(self):
        event = {"id": "specific", "imageUrl": "https://example.com/product.jpg"}
        apply_reborn_image(event)
        self.assertEqual(event["imageUrl"], "https://example.com/product.jpg")
        event = {"id": "specific"}
        apply_reborn_image(event, {"default": {"imageUrl": "reference.jpg"}, "items": {"specific": {"imageUrl": "product.jpg", "imageKind": "product"}}})
        self.assertEqual(event["imageKind"], "product")
        self.assertEqual(event["imageUrl"], "product.jpg")


if __name__ == "__main__":
    unittest.main()
