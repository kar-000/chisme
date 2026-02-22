export function ServerIcon({ server, isActive, onClick }) {
  const initials = server.name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')

  return (
    <button
      className={`server-icon${isActive ? ' server-icon--active' : ''}`}
      onClick={onClick}
      title={server.name}
      type="button"
    >
      {server.icon_url ? (
        <img src={server.icon_url} alt={server.name} />
      ) : (
        <span className="server-icon__initials">{initials}</span>
      )}
    </button>
  )
}
