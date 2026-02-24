const STATUS_COLORS = {
  online: 'var(--crt-teal)',
  away: 'var(--crt-orange)',
  dnd: '#ff4444',
  offline: 'var(--text-muted)',
}

/**
 * Small colored dot showing a user's presence status.
 * Pass inQuietHours=true to overlay a moon icon instead of the dot.
 * @param {string} status - 'online' | 'away' | 'dnd' | 'offline'
 * @param {'sm'|'md'|'lg'} size
 * @param {boolean} inQuietHours
 */
export default function StatusIndicator({ status = 'offline', size = 'sm', inQuietHours = false }) {
  const px = size === 'lg' ? 12 : size === 'md' ? 10 : 8

  if (inQuietHours) {
    return (
      <span
        title="quiet hours / do not disturb"
        style={{ fontSize: px, lineHeight: 1, flexShrink: 0 }}
      >
        🌙
      </span>
    )
  }

  const color = STATUS_COLORS[status] ?? STATUS_COLORS.offline

  return (
    <span
      title={status}
      style={{
        display: 'inline-block',
        width: px,
        height: px,
        borderRadius: '50%',
        background: color,
        boxShadow: `0 0 5px ${color}`,
        flexShrink: 0,
      }}
    />
  )
}
