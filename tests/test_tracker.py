"""
Tests for tracker.py (with a real, but temporary database).
setUp() creates a fresh test database before EVERY test,
tearDown() deletes it afterwards -> your real data is never touched.
"""

import os
import unittest
from datetime import date, datetime

import tracker
from seed_data import seed

TEST_DB = "test_timetracker.db"


class TestTracker(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        seed(TEST_DB, with_entries=False)  # E002 = Developer (90 EUR/h), P001 = project

    def tearDown(self):
        os.remove(TEST_DB)

    def test_start_and_stop_timer(self):
        start = datetime(2026, 11, 10, 9, 0)
        stop = datetime(2026, 11, 10, 10, 30)
        tracker.start_timer("E002", "P001", "Coding", now=start, db_path=TEST_DB)
        hours = tracker.stop_timer("E002", now=stop, db_path=TEST_DB)
        self.assertEqual(hours, 1.5)

        entries = tracker.get_entries_with_costs(db_path=TEST_DB)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["cost"], 135.0)  # 1.5 h * 90

    def test_second_timer_not_allowed(self):
        tracker.start_timer("E002", "P001", "Coding", db_path=TEST_DB)
        with self.assertRaises(ValueError):
            tracker.start_timer("E002", "P001", "More coding", db_path=TEST_DB)

    def test_stop_without_timer_raises(self):
        with self.assertRaises(ValueError):
            tracker.stop_timer("E002", db_path=TEST_DB)

    def test_unknown_person_raises(self):
        with self.assertRaises(ValueError):
            tracker.start_timer("X999", "P001", "Coding", db_path=TEST_DB)

    def test_manual_entry_uses_role_rate(self):
        tracker.add_manual_entry("E001", "P001", "Planning", date(2026, 11, 10), 2,
                                 db_path=TEST_DB)
        entries = tracker.get_entries_with_costs(db_path=TEST_DB)
        self.assertEqual(entries[0]["rate"], 120.0)  # Project Manager
        self.assertEqual(entries[0]["cost"], 240.0)

    def test_manual_entry_zero_hours_raises(self):
        with self.assertRaises(ValueError):
            tracker.add_manual_entry("E001", "P001", "Planning", date(2026, 11, 10), 0,
                                     db_path=TEST_DB)

    def test_invoice_only_billable(self):
        tracker.add_manual_entry("E002", "P001", "Coding", date(2026, 11, 10), 2,
                                 db_path=TEST_DB)
        tracker.add_manual_entry("E002", "P001", "Internal meeting", date(2026, 11, 10), 1,
                                 billable=False, db_path=TEST_DB)
        invoice = tracker.create_invoice("P001", db_path=TEST_DB)
        self.assertEqual(len(invoice["lines"]), 1)
        self.assertEqual(invoice["totals"]["net"], 180.0)
        self.assertEqual(invoice["totals"]["gross"], 216.0)

    def test_short_timer_counts_minutes(self):
        start = datetime(2026, 11, 10, 9, 0, 0)
        stop = datetime(2026, 11, 10, 9, 2, 10)  # 2 min 10 s -> 3 minutes
        tracker.start_timer("E002", "P001", "Quick fix", now=start, db_path=TEST_DB)
        hours = tracker.stop_timer("E002", now=stop, db_path=TEST_DB)
        self.assertEqual(hours, 0.05)


if __name__ == "__main__":
    unittest.main()
