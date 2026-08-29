"""Verify Zavis JSON-LD extraction."""

import unittest
from unittest.mock import patch

from extract_zavis import parse_directory_providers, parse_medical_business, parse_provider_detail, safe_fetch


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

    def test_extracts_detail_coordinates(self) -> None:
        html = '<script type="application/ld+json">{"@type":"MedicalBusiness","name":"Clinic","telephone":"+971 4 123 4567","geo":{"latitude":25.2,"longitude":55.3},"url":"https://example.test/clinic"}</script>'
        record = parse_provider_detail(html)
        self.assertEqual(record["lat"], "25.2")
        self.assertEqual(record["lon"], "55.3")

    @patch("extract_zavis.urlopen")
    def test_fetch_passes_request_timeout(self, urlopen_mock) -> None:
        """Pass the configured timeout to the public request boundary."""
        response = urlopen_mock.return_value.__enter__.return_value
        response.read.return_value = b"ok"
        from extract_zavis import fetch

        self.assertEqual(fetch("https://example.test", timeout=3), "ok")
        self.assertEqual(urlopen_mock.call_args.kwargs["timeout"], 3)

    @patch("extract_zavis.fetch", side_effect=TimeoutError("slow page"))
    def test_safe_fetch_skips_timeout(self, fetch_mock) -> None:
        """Treat a timed-out page as a failed page in a large crawl."""
        self.assertEqual(safe_fetch("https://example.test"), "")
        fetch_mock.assert_called_once_with("https://example.test", timeout=30)


if __name__ == "__main__":
    unittest.main()
