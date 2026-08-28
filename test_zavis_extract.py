"""Verify Zavis JSON-LD extraction."""

import unittest

from extract_zavis import parse_directory_providers, parse_medical_business


class ZavisExtractTest(unittest.TestCase):
    """Check the provider fields retained from a Zavis detail page."""

    def test_extracts_medical_business_fields(self) -> None:
        html = '<script type="application/ld+json">{"@type":"MedicalBusiness","name":"Clinic","areaServed":{"@type":"City","name":"Dubai"},"url":"https://example.test/clinic"}</script>'
        self.assertEqual(parse_medical_business(html)["name"], "Clinic")
        self.assertEqual(parse_medical_business(html)["city"], "Dubai")

    def test_extracts_directory_provider_cards(self) -> None:
        html = r'''\"id\":\"dha_1\",\"name\":\"Clinic\",\"slug\":\"clinic-dubai\",\"citySlug\":\"dubai\",\"categorySlug\":\"clinics\",\"address\":\"Main Street\",\"googleRating\":\"0\",\"googleReviewCount\":0,\"insurance\":[\"ADNIC\"],\"languages\":[\"English\"]'''
        record = parse_directory_providers(html)[0]
        self.assertEqual(record["id"], "dha_1")
        self.assertEqual(record["insurance"], "ADNIC")
        self.assertEqual(record["languages"], "English")


if __name__ == "__main__":
    unittest.main()
