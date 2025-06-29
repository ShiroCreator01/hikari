# Copyright (c) 2020 Nekokatt
# Copyright (c) 2021-present davfsa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Utility methods used for parsing timestamps and datetimes from Discord."""

from __future__ import annotations

__all__: typing.Sequence[str] = (
    "DISCORD_EPOCH",
    "Intervalish",
    "datetime_to_discord_epoch",
    "discord_epoch_to_datetime",
    "local_datetime",
    "time",
    "time_ns",
    "timespan_to_int",
    "unix_epoch_to_datetime",
    "utc_datetime",
    "uuid",
)

import datetime
import time as time_
import typing
import uuid as uuid_

Intervalish = typing.Union[int, float, datetime.timedelta]
"""Type hint representing a naive time period or time span.

This is a type that is like an interval of some sort.

This is an alias for [typing.Union[int, float, datetime.datetime]][],
where [`int`][] and [`float`][] types are interpreted as a number of seconds.
"""

DISCORD_EPOCH: typing.Final[datetime.timedelta] = datetime.timedelta(seconds=1_420_070_400)
"""Discord epoch used within snowflake identifiers.

This is defined as the timedelta of seconds between
`1/1/1970 00:00:00 UTC` and `1/1/2015 00:00:00 UTC`.

References
----------
* [Discord API documentation - Snowflakes](https://discord.com/developers/docs/reference#snowflakes)
"""


# Default to the standard lib parser, that isn't really ISO compliant but seems
# to work for what we need.
def slow_iso8601_datetime_string_to_datetime(datetime_str: str) -> datetime.datetime:
    """Parse an ISO-8601-like datestring into a datetime.

    Parameters
    ----------
    datetime_str
        The date string to parse.

    Returns
    -------
    datetime.datetime
        The corresponding date time.
    """
    if datetime_str.endswith(("z", "Z")):
        # Python's parser cannot handle zulu time, it isn't a proper ISO-8601 compliant parser.
        datetime_str = datetime_str[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(datetime_str)


fast_iso8601_datetime_string_to_datetime: typing.Callable[[str], datetime.datetime] | None
try:
    # CISO8601 is around 600x faster than modules like dateutil, which is
    # going to be noticeable on big bots where you are parsing hundreds of
    # thousands of "joined_at" fields on users on startup.
    import ciso8601

    # Discord appears to actually use RFC-3339, which isn't a true ISO-8601 implementation,
    # but somewhat of a subset with some edge cases.
    # See https://tools.ietf.org/html/rfc3339#section-5.6
    fast_iso8601_datetime_string_to_datetime = ciso8601.parse_rfc3339

except ModuleNotFoundError:
    fast_iso8601_datetime_string_to_datetime = None

iso8601_datetime_string_to_datetime: typing.Callable[[str], datetime.datetime] = (
    fast_iso8601_datetime_string_to_datetime or slow_iso8601_datetime_string_to_datetime
)


def discord_epoch_to_datetime(epoch: int, /) -> datetime.datetime:
    """Parse a Discord epoch into a [`datetime.datetime`][] object.

    Parameters
    ----------
    epoch
        Number of milliseconds since [1/1/2015 00:00:00 UTC][].

    Returns
    -------
    datetime.datetime
        Number of seconds since [1/1/1970 00:00:00 UTC][].
    """
    return datetime.datetime.fromtimestamp(epoch / 1_000, datetime.timezone.utc) + DISCORD_EPOCH


def datetime_to_discord_epoch(timestamp: datetime.datetime) -> int:
    """Parse a [`datetime.datetime`][] object into an [`int`][] `DISCORD_EPOCH` offset.

    Parameters
    ----------
    timestamp
        Number of seconds since `1/1/1970 00:00:00 UTC`.

    Returns
    -------
    int
        Number of milliseconds since `1/1/2015 00:00:00 UTC`.
    """
    return int((timestamp - DISCORD_EPOCH).timestamp() * 1_000)


def unix_epoch_to_datetime(epoch: float, /, *, is_millis: bool = True) -> datetime.datetime:
    """Parse a UNIX epoch to a [`datetime.datetime`][] object.

    !!! note
        If an epoch that's outside the range of what this system can handle,
        this will return [`datetime.datetime.max`][] if the timestamp is positive,
        or [`datetime.datetime.min`][] otherwise.

    Parameters
    ----------
    epoch
        Number of seconds/milliseconds since [1/1/1970 00:00:00 UTC][].
    is_millis
        [`True`][] by default, indicates the input timestamp is measured in
        milliseconds rather than seconds.

    Returns
    -------
    datetime.datetime
        Number of seconds since [1/1/1970 00:00:00 UTC][].
    """
    # Datetime seems to raise an OSError when you try to convert an out of range timestamp on Windows and a ValueError
    # if you try on a UNIX system so we want to catch both.
    try:
        epoch /= (is_millis * 1_000) or 1
        return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)
    except (OSError, ValueError):
        if epoch > 0:
            return datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)


def timespan_to_int(value: Intervalish, /) -> int:
    """Cast the given timespan in seconds to an integer value.

    Parameters
    ----------
    value
        The number of seconds.

    Returns
    -------
    int
        The integer number of seconds. Fractions are discarded. Negative values
        are removed.
    """
    if isinstance(value, datetime.timedelta):
        value = value.total_seconds()
    return int(max(0, value))


def local_datetime() -> datetime.datetime:
    """Return the current date/time for the system's time zone."""
    return utc_datetime().astimezone()


def utc_datetime() -> datetime.datetime:
    """Return the current date/time for UTC (GMT+0)."""
    return datetime.datetime.now(tz=datetime.timezone.utc)


if typing.TYPE_CHECKING:

    def time() -> float:
        """Epoch time in seconds (since 00:00:00 UTC on January 1, 1970)."""
        raise NotImplementedError

    def time_ns() -> int:
        """Epoch time in nanoseconds (since 00:00:00 UTC on January 1, 1970)."""
        raise NotImplementedError

else:
    time = time_.time
    """Epoch time in seconds (since 00:00:00 UTC on January 1, 1970)."""

    time_ns = time_.time_ns
    """Epoch time in nanoseconds (since 00:00:00 UTC on January 1, 1970)."""


def uuid() -> str:
    """Generate a unique UUID (1ns precision)."""
    return uuid_.uuid1(None, time_ns()).hex
