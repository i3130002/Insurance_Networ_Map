"""Verify Zavis JSON-LD extraction."""

import unittest

from extract_zavis import parse_medical_business


class ZavisExtractTest(unittest.TestCase):
    """Check the provider fields retained from a Zavis detail page."""

    def test_extracts_medical_business_fields(self) -> None:
        html = '<script type="application/ld+json">{"@type":"MedicalBusiness","name":"Clinic","areaServed":{"@type":"City","name":"Dubai"},"url":"https://example.test/clinic"}</script>'
        self.assertEqual(parse_medical_business(html)["name"], "Clinic")
        self.assertEqual(parse_medical_business(html)["city"], "Dubai")


if __name__ == "__main__":
    unittest.main()
