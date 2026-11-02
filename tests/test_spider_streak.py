"""Tests for the Spider Streak contribution record calculation."""

import datetime as dt
import unittest

from scripts.render_spider_streak import streak_stats


class StreakStatsTests(unittest.TestCase):
    def test_historical_record_survives_broken_current_streak(self):
        today = dt.date(2026, 11, 2)
        days = {today - dt.timedelta(days=i): 1 for i in range(10, 15)}
        days[today - dt.timedelta(days=1)] = 1
        current, highest, dates = streak_stats(days, today)
        self.assertEqual((current, highest), (1, 5))
        self.assertEqual(dates, {today - dt.timedelta(days=1)})

    def test_new_record_updates_all_time_high(self):
        today = dt.date(2026, 11, 2)
        days = {today - dt.timedelta(days=i): 1 for i in range(6)}
        current, highest, _ = streak_stats(days, today)
        self.assertEqual((current, highest), (6, 6))

    def test_missing_dates_break_streaks(self):
        today = dt.date(2026, 11, 2)
        days = {
            today - dt.timedelta(days=6): 1,
            today - dt.timedelta(days=5): 1,
            today - dt.timedelta(days=3): 1,
            today - dt.timedelta(days=2): 0,
        }
        self.assertEqual(streak_stats(days, today)[:2], (0, 2))

    def test_today_may_be_unfinished(self):
        today = dt.date(2026, 11, 2)
        days = {
            today - dt.timedelta(days=2): 1,
            today - dt.timedelta(days=1): 1,
            today: 0,
        }
        self.assertEqual(streak_stats(days, today)[:2], (2, 2))

    def test_streak_crosses_year_boundary(self):
        today = dt.date(2026, 1, 2)
        days = {today - dt.timedelta(days=i): 1 for i in range(5)}
        self.assertEqual(streak_stats(days, today)[:2], (5, 5))


if __name__ == "__main__":
    unittest.main()
