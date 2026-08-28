"""Verify the user-facing insurance selection flow contract."""

import unittest
from pathlib import Path


class InsuranceSelectionFlowTest(unittest.TestCase):
    """Check the static page exposes the two-step selection flow."""

    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")

    def test_company_selection_precedes_plan_selection(self) -> None:
        """Require separate selectors and a company-driven plan population hook."""
        self.assertIn('id="insurerSelect"', self.html)
        self.assertIn('id="planSelect"', self.html)
        self.assertIn("populatePlanOptions", self.html)
        self.assertIn("getElementById('insurerSelect').addEventListener", self.html)
        self.assertIn("e['ZAVIS URL']", self.html)


if __name__ == "__main__":
    unittest.main()
