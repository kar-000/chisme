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

# Voice / WebRTC signaling
VOICE_JOIN = "voice.join"
VOICE_LEAVE = "voice.leave"
VOICE_STATE_UPDATE = "voice.state_update"
VOICE_OFFER = "voice.offer"
VOICE_ANSWER = "voice.answer"
VOICE_ICE_CANDIDATE = "voice.ice_candidate"
VOICE_USER_JOINED = "voice.user_joined"
VOICE_USER_LEFT = "voice.user_left"
VOICE_STATE_CHANGED = "voice.state_changed"
VOICE_STATE_SNAPSHOT = "voice.state_snapshot"
