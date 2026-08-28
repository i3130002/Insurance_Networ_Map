"""Verify one-time Zavis provider matching rules."""

import unittest

from match_zavis import city_to_emirate, phone_values


class ZavisMatchTest(unittest.TestCase):
    """Check identity normalization used by the crosswalk builder."""

    def test_city_and_phone_normalization(self) -> None:
        self.assertEqual(city_to_emirate("Ras Al Khaimah"), "RAK")
        self.assertEqual(phone_values("+971 4 226 3299"), {"42263299", "2263299"})


if __name__ == "__main__":
    unittest.main()
