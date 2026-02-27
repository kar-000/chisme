"""
Centralised notification gate.

All push / browser notifications should route through
is_user_in_quiet_hours() before dispatching so that DND and
scheduled quiet hours are honoured in one place.

should_notify_for_channel_message() and should_notify_for_dm() are the
single source of truth for "should this user receive a notification?".
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.user import User


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


def should_notify_for_channel_message(
    user: "User",
    *,
    sender_id: int,
    sender_username: str,
    content: str,
    channel_name: str,
    server_name: str,
    channel_id: int,
    db: "Session",
) -> tuple[bool, str, str, bool]:
    """Decide whether *user* should receive a notification for a channel message.

    Returns ``(should_notify, title, tag, is_mention)``.

    ``is_mention`` is True only when the notification fired because of a
    @username mention; it is False for keyword matches and the generic case.

    Priority:
      1. Own message → no notification
      2. Quiet hours / DND → no notification
      3. TODO: channel muting — skip muted channels when that feature is added
      4. Keyword match → notify with keyword title (is_mention=False)
      5. @mention → notify with mention title (is_mention=True)
      6. All other messages → notify with generic title (is_mention=False)
    """
    if user.id == sender_id:
        return False, "", "", False
    if is_user_in_quiet_hours(user):
        return False, "", "", False

    # TODO: add channel muting check here when implemented

    content_lower = (content or "").lower()

    # Keyword match
    if content_lower:
        from app.models.keyword import UserKeyword

        keyword_rows = db.query(UserKeyword).filter(UserKeyword.user_id == user.id).all()
        for kw_row in keyword_rows:
            if re.search(re.escape(kw_row.keyword), content_lower):
                title = f'Keyword "{kw_row.keyword}" in #{channel_name} · {server_name} from {sender_username}'
                return True, title, f"keyword-{channel_id}-{user.id}", False

    # @mention
    if content_lower and f"@{user.username.lower()}" in content_lower:
        title = f"{sender_username} mentioned you in #{channel_name} · {server_name}"
        return True, title, f"mention-{channel_id}-{user.id}", True

    # Generic
    title = f"{sender_username} in #{channel_name} · {server_name}"
    return True, title, f"msg-{channel_id}", False


def should_notify_for_dm(
    user: "User",
    *,
    sender_id: int,
    sender_username: str,
) -> tuple[bool, str, str]:
    """Decide whether *user* should receive a notification for an incoming DM.

    Returns ``(should_notify, title, tag)``.
    """
    if user.id == sender_id:
        return False, "", ""
    if is_user_in_quiet_hours(user):
        return False, "", ""
    return True, f"DM from {sender_username}", f"dm-{user.id}"
