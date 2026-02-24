"""
Centralised notification gate.

All push / browser notifications should route through
is_user_in_quiet_hours() before dispatching so that DND and
scheduled quiet hours are honoured in one place.
"""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def is_user_in_quiet_hours(user) -> bool:
    """Return True if the user should NOT receive notifications right now.

    Priority order:
      1. dnd_override == "on"  → always suppress
      2. dnd_override == "off" → always allow
      3. Use schedule (quiet_hours_enabled + start/end/tz)
    """
    if user.dnd_override == "on":
        return True
    if user.dnd_override == "off":
        return False

    if not user.quiet_hours_enabled or not user.quiet_hours_start:
        return False

    try:
        tz = ZoneInfo(user.quiet_hours_tz or "UTC")
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")

    now = datetime.now(tz).time()
    start = user.quiet_hours_start
    end = user.quiet_hours_end

    if end is None:
        return False

    # Handle overnight windows (e.g. 23:00 – 08:00)
    if start > end:
        return now >= start or now < end
    return start <= now < end
