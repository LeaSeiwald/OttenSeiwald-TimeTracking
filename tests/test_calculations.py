import unittest
from datetime import datetime

from calculations import *


class TestDuration(unittest.TestCase):
    def test_duration_hours(self):
        start = datetime(2026, 11, 10, 9, 0)
        end = datetime(2026, 11, 10, 11, 30)
        self.assertEqual(calculate_duration_hours(start, end), 2.5)

    def test_duration_zero(self):
        start = datetime(2026, 11, 10, 9, 0)
        self.assertEqual(calculate_duration_hours(start, start), 0)

    def test_duration_over_midnight(self):
        start = datetime(2026, 11, 10, 23, 0)
        end = datetime(2026, 11, 11, 1, 0)
        self.assertEqual(calculate_duration_hours(start, end), 2)

    def test_one_minute(self):
        start = datetime(2026, 11, 10, 9, 0, 0)
        end = datetime(2026, 11, 10, 9, 1, 0)
        self.assertEqual(calculate_duration_hours(start, end), 0.02)

    def test_started_minute_counts(self):
        start = datetime(2026, 11, 10, 9, 0, 0)
        end = datetime(2026, 11, 10, 9, 0, 20)  # 20 seconds -> 1 minute
        self.assertEqual(calculate_duration_minutes(start, end), 1)
        self.assertEqual(calculate_duration_hours(start, end), 0.02)

    def test_end_before_start_raises(self):
        start = datetime(2026, 11, 10, 12, 0)
        end = datetime(2026, 11, 10, 9, 0)
        with self.assertRaises(ValueError):
            calculate_duration_hours(start, end)


class TestRatesAndCosts(unittest.TestCase):
    def setUp(self):
        self.rates = {"Developer": 90.0, "Consultant": 110.0}

    def test_rate_for_role(self):
        self.assertEqual(get_rate_for_role("Developer", self.rates), 90.0)

    def test_unknown_role_raises(self):
        with self.assertRaises(KeyError):
            get_rate_for_role("Designer", self.rates)

    def test_cost(self):
        self.assertEqual(calculate_cost(2.5, 90), 225.0)

    def test_cost_rounding(self):
        self.assertAlmostEqual(calculate_cost(0.33, 110), 36.3)

    def test_negative_hours_raises(self):
        with self.assertRaises(ValueError):
            calculate_cost(-1, 90)


class TestInvoiceTotals(unittest.TestCase):
    def test_totals(self):
        entries = [{"hours": 2, "rate": 90}, {"hours": 1.5, "rate": 120}]
        totals = calculate_invoice_totals(entries)
        self.assertEqual(totals["total_hours"], 3.5)
        self.assertEqual(totals["net"], 360.0)
        self.assertEqual(totals["vat"], 72.0)
        self.assertEqual(totals["gross"], 432.0)

    def test_empty_invoice(self):
        totals = calculate_invoice_totals([])
        self.assertEqual(totals["gross"], 0)

    def test_sum_costs_by_project(self):
        entries = [
            {"project_id": "P1", "hours": 1, "rate": 100},
            {"project_id": "P1", "hours": 2, "rate": 100},
            {"project_id": "P2", "hours": 1, "rate": 50},
        ]
        result = sum_costs_by(entries, "project_id")
        self.assertEqual(result["P1"]["hours"], 3)
        self.assertEqual(result["P1"]["cost"], 300)
        self.assertEqual(result["P2"]["cost"], 50)


class TestBudget(unittest.TestCase):
    def test_budget_ok(self):
        self.assertEqual(check_budget_status(500, 1000), "ok")

    def test_budget_warning_at_80_percent(self):
        self.assertEqual(check_budget_status(800, 1000), "warning")

    def test_budget_exceeded(self):
        self.assertEqual(check_budget_status(1200, 1000), "exceeded")

    def test_no_budget(self):
        self.assertEqual(check_budget_status(500, None), "no budget")


if __name__ == "__main__":
    unittest.main()
