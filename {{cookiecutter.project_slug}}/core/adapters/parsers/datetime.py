# core/adapters/parsers/datetime.py
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Union


class Datetime:
    """A timezone-aware datetime object that is always in UTC and serializable."""

    def __init__(self, dtime: Optional[Union[datetime, str]] = None):
        """Initialize with either a datetime object or ISO format string."""
        if dtime is None:
            dtime = datetime.now(timezone.utc)
        elif isinstance(dtime, str):
            dtime = dtime.replace('Z', '+00:00').replace('+00:00+00:00', '+00:00')
            dtime = datetime.fromisoformat(dtime)
        if dtime.tzinfo is None:
            dtime = dtime.replace(tzinfo=timezone.utc)
        elif dtime.tzinfo != timezone.utc:
            dtime = dtime.astimezone(timezone.utc)
        assert isinstance(dtime, datetime)
        self._dt = dtime

    def __str__(self) -> str:
        """Convert to string (ISO format)."""
        return self.to_str()

    def __repr__(self) -> str:
        """Developer representation."""
        return f"UTCDateTime('{self.isoformat()}')"

    def __eq__(self, other: object) -> bool:
        """Compare equality with another UTCDateTime."""
        if other is None:
            raise TypeError("can't compare datetime.datetime to NoneType")
        if isinstance(other, Datetime):
            return self._dt == other._dt
        if isinstance(other, datetime):
            return self._dt == other
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        """Compare less than with another UTCDateTime."""
        if other is None:
            raise TypeError("can't compare datetime.datetime to NoneType")
        if isinstance(other, Datetime):
            return self._dt < other._dt
        if isinstance(other, datetime):
            return self._dt < other
        return NotImplemented

    def __hash__(self) -> int:
        """Make hashable for use in sets/dicts."""
        return hash(self._dt)

    def __getattr__(self, name: str):
        """Delegate any unhandled attributes to the underlying datetime."""
        return getattr(self._dt, name)

    @property
    def datetime(self):
        return self._dt

    @classmethod
    def now(cls) -> 'Datetime':
        """Create a new UTCDateTime with the current time."""
        return cls(datetime.now(timezone.utc))

    @classmethod
    def rand_from_now(cls, seconds: float = 0.0, hours: float = 0.0, days: float = 0.0,
                      cooldown_seconds: float = 120.0) -> 'Datetime':
        """
        Create a new UTCDateTime within a time range starting after a cooldown period.

        Args:
            seconds: Number of seconds in the random window
            hours: Number of hours in the random window
            days: Number of days in the random window
            cooldown_seconds: Base offset from now where the random window starts

        Returns:
            A new Datetime object between (now + cooldown_seconds) and
            (now + cooldown_seconds + (seconds + hours*3600 + days*86400))
        """
        total_seconds = seconds + hours * 3600 + days * 86400
        if total_seconds == 0:
            total_seconds = 3600 * 24  # Default to 24 hours if no range specified

        now = datetime.now(timezone.utc)

        # Start time is now + cooldown
        start_time = now + timedelta(seconds=cooldown_seconds)

        # Generate random time between start_time and start_time + total_seconds
        random_offset = random.random() * total_seconds
        random_time = start_time + timedelta(seconds=random_offset)

        return cls(random_time)

    def add_time(self, seconds: float = 0.0, hours: float = 0.0, days: float = 0.0):
        """
        Add/subtract time inline like my_dt.add_time(hours=4).to_str()
        """
        total_seconds = seconds + hours * 3600 + days * 86400
        self._dt += timedelta(seconds=total_seconds)
        return self


    @classmethod
    def from_timestamp(cls, timestamp: float) -> 'Datetime':
        """Create a new UTCDateTime from a UNIX timestamp."""
        return cls(datetime.fromtimestamp(timestamp, tz=timezone.utc))

    @classmethod
    def from_str(cls, date_string: str) -> 'Datetime':
        """Create a new UTCDateTime from an ISO format string."""
        return cls(date_string)

    def to_timestamp(self) -> float:
        """Convert to UNIX timestamp."""
        return self._dt.timestamp()

    def to_str(self) -> str:
        """Convert to ISO 8601 format string."""
        return self._dt.isoformat().replace('+00:00', 'Z').replace('+00:00+00:00', '+00:00')

    def to_str_yyyy_mm_dd(self) -> str:
        """Convert to a simple date string"""
        return self._dt.strftime('%Y_%m_%d')


def datetime_now() -> datetime:
    """ Simple UTC_now factory"""
    return Datetime().datetime
