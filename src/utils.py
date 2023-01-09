import datetime as dt
import re
from email.utils import format_datetime, parsedate_to_datetime


_iso8601_datetime_re = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
    r"[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})"
    r"(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?"
    r"(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$"
)

_iso8601_date_re = re.compile(r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})$")

_iso8601_time_re = re.compile(
    r"(?P<hour>\d{1,2}):(?P<minute>\d{1,2})"
    r"(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?"
)


def isoformat(datetime: dt.datetime) -> str:
    """Return the ISO8601-formatted representation of a datetime object.

    :param datetime datetime: The datetime.
    """
    return datetime.isoformat()


def rfcformat(datetime: dt.datetime) -> str:
    """Return the RFC822-formatted representation of a datetime object.

    :param datetime datetime: The datetime.
    """
    return format_datetime(datetime)


def get_fixed_timezone(offset: int | float | dt.timedelta) -> dt.timezone:
    """Return a tzinfo instance with a fixed offset from UTC."""
    if isinstance(offset, dt.timedelta):
        offset = offset.total_seconds() // 60
    sign = "-" if offset < 0 else "+"
    hhmm = "%02d%02d" % divmod(abs(offset), 60)
    name = sign + hhmm
    return dt.timezone(dt.timedelta(minutes=offset), name)


def from_iso_datetime(value):
    """Parse a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.
    """
    match = _iso8601_datetime_re.match(value)
    if not match:
        raise ValueError("Not a valid ISO8601-formatted datetime string")
    kw = match.groupdict()
    kw["microsecond"] = kw["microsecond"] and kw["microsecond"].ljust(6, "0")
    tzinfo = kw.pop("tzinfo")
    if tzinfo == "Z":
        tzinfo = dt.timezone.utc
    elif tzinfo is not None:
        offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
        offset = 60 * int(tzinfo[1:3]) + offset_mins
        if tzinfo[0] == "-":
            offset = -offset
        tzinfo = get_fixed_timezone(offset)
    kw = {k: int(v) for k, v in kw.items() if v is not None}
    kw["tzinfo"] = tzinfo
    return dt.datetime(**kw)


def from_rfc(datestring: str) -> dt.datetime:
    """Parse a RFC822-formatted datetime string and return a datetime object.

    https://stackoverflow.com/questions/885015/how-to-parse-a-rfc-2822-date-time-into-a-python-datetime  # noqa: B950
    """
    return parsedate_to_datetime(datestring)
