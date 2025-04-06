import unittest
from datetime import datetime, timezone, timedelta
import time
from core.adapters.parsers.datetime import Datetime


class TestDatetime(unittest.TestCase):
    def test_init_default(self):
        """Test initialization with no arguments"""
        # Add a small buffer for timing variations
        before = time.time() - 0.1  # 100ms buffer before
        dt = Datetime()
        after = time.time() + 0.1  # 100ms buffer after

        self.assertIsNotNone(dt._dt.tzinfo)
        self.assertEqual(dt._dt.tzinfo, timezone.utc)
        timestamp = dt.to_timestamp()
        self.assertTrue(
            before <= timestamp <= after,
            f"Timestamp {timestamp} not within range [{before}, {after}]"
        )

    def test_init_from_naive_datetime(self):
        """Test initialization with timezone-naive datetime"""
        naive_dt = datetime(2024, 1, 13, 12, 30, 45)
        dt = Datetime(naive_dt)

        self.assertEqual(dt._dt.year, 2024)
        self.assertEqual(dt._dt.month, 1)
        self.assertEqual(dt._dt.day, 13)
        self.assertEqual(dt._dt.hour, 12)
        self.assertEqual(dt._dt.minute, 30)
        self.assertEqual(dt._dt.second, 45)
        self.assertEqual(dt._dt.tzinfo, timezone.utc)

    def test_init_from_aware_datetime(self):
        """Test initialization with timezone-aware datetime"""
        # Create a datetime with EST timezone (UTC-5)
        est_offset = timedelta(hours=-5)
        est_tz = timezone(est_offset)
        aware_dt = datetime(2024, 1, 13, 12, 30, 45, tzinfo=est_tz)
        dt = Datetime(aware_dt)

        # Should be converted to UTC (12:30 EST = 17:30 UTC)
        self.assertEqual(dt._dt.hour, 17)
        self.assertEqual(dt._dt.tzinfo, timezone.utc)

    def test_init_from_string(self):
        """Test initialization from ISO format string"""
        # Test with Z suffix
        dt1 = Datetime("2024-01-13T12:30:45Z")
        self.assertEqual(dt1._dt.hour, 12)

        # Test with +00:00 suffix
        dt2 = Datetime("2024-01-13T12:30:45+00:00")
        self.assertEqual(dt2._dt.hour, 12)

        # Test with different timezone offset
        dt3 = Datetime("2024-01-13T12:30:45+05:00")
        self.assertEqual(dt3._dt.hour, 7)  # 12:30 UTC+5 = 07:30 UTC

    def test_now(self):
        """Test class method now()"""
        # Add a small buffer for timing variations
        before = time.time() - 0.1  # 100ms buffer before
        dt = Datetime.now()
        after = time.time() + 0.1  # 100ms buffer after

        timestamp = dt.to_timestamp()
        self.assertTrue(
            before <= timestamp <= after,
            f"Timestamp {timestamp} not within range [{before}, {after}]"
        )
        self.assertEqual(dt._dt.tzinfo, timezone.utc)

    def test_timestamp_conversion(self):
        """Test timestamp conversion reversibility"""
        timestamp = 1705152645.0  # 2024-01-13 12:30:45 UTC
        dt = Datetime.from_timestamp(timestamp)

        self.assertEqual(dt.to_timestamp(), timestamp)
        self.assertEqual(dt._dt.tzinfo, timezone.utc)

    def test_string_conversion(self):
        """Test string conversion reversibility"""
        original = "2024-01-13T12:30:45Z"
        dt = Datetime.from_str(original)
        converted = dt.to_str()

        self.assertEqual(converted, original)
        self.assertEqual(dt._dt.tzinfo, timezone.utc)

    def test_comparison(self):
        """Test comparison operators"""
        dt1 = Datetime("2024-01-13T12:30:45Z")
        dt2 = Datetime("2024-01-13T12:30:45Z")
        dt3 = Datetime("2024-01-13T12:30:46Z")

        self.assertEqual(dt1, dt2)
        self.assertNotEqual(dt1, dt3)
        self.assertLess(dt1, dt3)
        self.assertGreater(dt3, dt1)

    def test_hashable(self):
        """Test hashable behavior"""
        dt1 = Datetime("2024-01-13T12:30:45Z")
        dt2 = Datetime("2024-01-13T12:30:45Z")

        # Should be usable as dictionary keys
        d = {dt1: "value"}
        self.assertEqual(d[dt2], "value")

        # Should be usable in sets
        s = {dt1, dt2}
        self.assertEqual(len(s), 1)

    def test_attribute_delegation(self):
        """Test delegation of datetime attributes"""
        dt = Datetime("2024-01-13T12:30:45Z")

        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 13)
        self.assertEqual(dt.hour, 12)
        self.assertEqual(dt.minute, 30)
        self.assertEqual(dt.second, 45)

        # Test method delegation
        self.assertEqual(
            dt.strftime("%Y-%m-%d %H:%M:%S"),
            "2024-01-13 12:30:45"
        )

    def test_invalid_inputs(self):
        """Test handling of invalid inputs"""
        with self.assertRaises(ValueError):
            Datetime("invalid-date-string")

        with self.assertRaises(AttributeError):
            # noinspection PyStatementEffect
            Datetime().nonexistent_attribute

    def test_str_representation(self):
        """Test string representation"""
        dt = Datetime("2024-01-13T12:30:45Z")
        # Test __str__ method
        self.assertEqual(str(dt), "2024-01-13T12:30:45Z")
        # Verify it matches to_str() output
        self.assertEqual(str(dt), dt.to_str())

    def test_repr_representation(self):
        """Test developer representation"""
        dt = Datetime("2024-01-13T12:30:45Z")
        expected_repr = "UTCDateTime('2024-01-13T12:30:45+00:00')"
        self.assertEqual(repr(dt), expected_repr)

    def test_comparison_edge_cases(self):
        """Test comparison operators with different types"""
        dt = Datetime("2024-01-13T12:30:45Z")
        native_dt = datetime(2024, 1, 13, 12, 30, 45, tzinfo=timezone.utc)

        # Test equality with native datetime
        self.assertEqual(dt, native_dt)

        # Test less than with native datetime
        self.assertLess(dt, native_dt + timedelta(seconds=1))

        # Test comparison with non-datetime object
        with self.assertRaises(TypeError):
            dt < None

        with self.assertRaises(TypeError):
            dt == None

    def test_rand_from_now(self):
        """Test random datetime generation within specified ranges"""
        # Use a fixed reference time for all comparisons
        now = Datetime.now()
        cooldown = 120  # Default cooldown in seconds

        # Test with seconds
        dt1 = Datetime.rand_from_now(seconds=60)
        self.assertTrue(
            now._dt + timedelta(seconds=cooldown + 60) >= dt1._dt >= now._dt + timedelta(seconds=cooldown),
            f"Generated time {dt1._dt} not within expected range"
        )

        # Test with hours
        dt2 = Datetime.rand_from_now(hours=2)
        self.assertTrue(
            now._dt + timedelta(seconds=cooldown + 2*3600) >= dt2._dt >= now._dt + timedelta(seconds=cooldown),
            f"Generated time {dt2._dt} not within expected range"
        )

        # Test with days
        dt3 = Datetime.rand_from_now(days=1)
        self.assertTrue(
            now._dt + timedelta(seconds=cooldown + 86400) >= dt3._dt >= now._dt + timedelta(seconds=cooldown),
            f"Generated time {dt3._dt} not within expected range"
        )

        # Test with combination and custom cooldown
        custom_cooldown = 30
        dt4 = Datetime.rand_from_now(seconds=30, hours=1, cooldown_seconds=custom_cooldown)
        total_seconds = 30 + 3600  # seconds + hours in seconds
        self.assertTrue(
            now._dt + timedelta(seconds=custom_cooldown + total_seconds) >= dt4._dt >= now._dt + timedelta(seconds=custom_cooldown),
            f"Generated time {dt4._dt} not within expected range"
        )

        # Test default behavior (24 hours) when no duration specified
        dt5 = Datetime.rand_from_now()
        self.assertTrue(
            now._dt + timedelta(seconds=cooldown + 24*3600) >= dt5._dt >= now._dt + timedelta(seconds=cooldown),
            f"Generated time {dt5._dt} not within expected range"
        )


if __name__ == '__main__':
    unittest.main()
