"""Read-only regression tests for CROW Merchant return policy labels."""
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

MODULE_PATH = Path(__file__).with_name("generate_merchant_feed.py")
spec = importlib.util.spec_from_file_location("generate_merchant_feed", MODULE_PATH)
merchant = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merchant)

NS = {"g": merchant.NAMESPACE}


class ReturnPolicyLabelTests(unittest.TestCase):
    def test_only_explicit_hygiene_categories_are_tagged(self):
        for category in ("Aretes", "Arete", "Piercings", "Piercing", "áretes"):
            with self.subTest(category=category):
                self.assertEqual(
                    merchant.return_policy_label(category),
                    "CROW-SIN-CAMBIOS-HIGIENE",
                )
        for category in ("Collares", "Anillos", "Pulseras", "Polos", "Earcuffs", "Charms"):
            with self.subTest(category=category):
                self.assertIsNone(merchant.return_policy_label(category))

    def test_generated_feed_tags_exceptions_without_changing_other_items(self):
        categories = ["Aretes", "Piercings", "Collares", "Anillos", "Earcuffs", "Polos"]
        products = [
            {
                "id": str(i),
                "sku": "CROW-TEST-" + str(i),
                "name": "Test " + str(i),
                "category": category,
                "price": "49.90",
                "sale_price": "0",
                "stock": 2,
                "product_type": "commerce",
                "status": "published",
                "activo_peru": True,
                "available_pe": True,
                "image_url": "https://example.com/image-" + str(i) + ".png",
                "description": "Prueba de catálogo",
            }
            for i, category in enumerate(categories, start=1)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            previous_dir = os.getcwd()
            try:
                os.chdir(tmp)
                with patch.dict(os.environ, {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_PUBLISHABLE_KEY": "test-public-key",
                }):
                    with patch.object(
                        merchant.urllib.request,
                        "urlopen",
                        return_value=io.BytesIO(json.dumps(products).encode("utf-8")),
                    ):
                        merchant.main()
                doc = ET.parse("google-merchant-pe.xml")
                items = doc.findall("./channel/item")
                self.assertEqual(len(items), len(products))
                for category, item in zip(categories, items):
                    label = item.findtext("g:return_policy_label", namespaces=NS)
                    expected = merchant.return_policy_label(category)
                    self.assertEqual(label, expected, category)
                    self.assertEqual(item.findtext("g:price", namespaces=NS), "49.90 PEN")
                    self.assertEqual(item.findtext("g:availability", namespaces=NS), "in_stock")
            finally:
                os.chdir(previous_dir)


if __name__ == "__main__":
    unittest.main()
