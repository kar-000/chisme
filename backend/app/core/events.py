# WebSocket event type definitions
# UI events are styled using warm CRT palette from COLOR_REFERENCE.md:
#   --crt-teal (#00CED1): primary message text
#   --crt-teal-light (#5DADE2): usernames / join events
#   --crt-pink (#FFB6C1): own messages
#   --crt-orange (#FF8C42): unread badges / system notices

MESSAGE_NEW = "message.new"
MESSAGE_UPDATED = "message.updated"
MESSAGE_DELETED = "message.deleted"

REACTION_ADDED = "reaction.added"
REACTION_REMOVED = "reaction.removed"

USER_JOINED = "user.joined"
USER_LEFT = "user.left"
USER_TYPING = "user.typing"

CHANNEL_CREATED = "channel.created"

PRESENCE_CHANGED = "presence.changed"
