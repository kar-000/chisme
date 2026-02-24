/**
 * Client-side quiet hours check — mirrors the backend is_user_in_quiet_hours logic.
 * Used to gate browser notifications without a round-trip to the server.
 *
 * @param {object} qh - quietHours object from authStore
 * @returns {boolean}
 */
export function isInQuietHours(qh) {
  if (!qh) return false
  if (qh.dnd_override === 'on') return true
  if (qh.dnd_override === 'off') return false
  if (!qh.enabled || !qh.start || !qh.end) return false

  const tz = qh.timezone || 'UTC'
  let nowStr
  try {
    nowStr = new Date().toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: tz,
    })
  } catch {
    nowStr = new Date().toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    })
  }

  const start = qh.start  // "HH:MM"
  const end = qh.end      // "HH:MM"
  const now = nowStr      // "HH:MM"

  // Overnight window (e.g., 23:00 – 08:00)
  if (start > end) {
    return now >= start || now < end
  }
  return now >= start && now < end
}
