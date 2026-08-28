"""Verify Takafol workbook normalization rules."""

import unittest

from import_takafol_networks import normalize_emirate, network_id_for


class TakafolImportTest(unittest.TestCase):
    """Check the stable mappings used by the workbook importer."""

    def test_normalizes_emirate_names_to_project_codes(self) -> None:
        """Map source spellings to the codes used by the registry."""
        self.assertEqual(normalize_emirate("Ras al Khaimah"), "RAK")
        self.assertEqual(normalize_emirate("United Arab Emirates"), "")

    def test_network_id_is_stable_and_slugged(self) -> None:
        """Create filesystem-safe IDs from downloaded workbook names."""
        self.assertEqual(network_id_for("NAS - Comprehensive Network.xlsx"), "nas-comprehensive-network")


if __name__ == "__main__":
    unittest.main()
