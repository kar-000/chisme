import { useState, useEffect } from 'react'
import api from '../services/api'
import useAuthStore from '../store/authStore'

/**
 * Operator Dashboard — accessible at /operator.
 * Visible only to users with is_site_admin = true.
 * Non-admins who navigate here are redirected to root.
 * react-router-dom is not available; routing is via window.location.
 */
export function OperatorDashboard() {
  const { user } = useAuthStore()
  const [servers, setServers] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Belt-and-suspenders frontend gate — the backend also enforces this
  if (user && !user.is_site_admin) {
    window.history.replaceState({}, '', '/')
    return null
  }

  useEffect(() => {
    Promise.all([
      api.get('/operator/servers'),
      api.get('/operator/users'),
    ])
      .then(([serversRes, usersRes]) => {
        setServers(serversRes.data)
        setUsers(usersRes.data)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="operator-loading">Loading…</div>
  if (error) return <div className="operator-error">{error}</div>

  return (
    <div className="operator-dashboard">
      <h1 className="operator-title">Operator Dashboard</h1>

      <section className="operator-section">
        <h2>
          Servers <span className="operator-count">({servers.length})</span>
        </h2>
        <table className="operator-table">
          <thead>
            <tr>
              <th>ID</th><th>Name</th><th>Slug</th><th>Owner ID</th>
              <th>Members</th><th>Status</th><th>Created</th>
            </tr>
          </thead>
          <tbody>
            {servers.map((s) => (
              <tr
                key={s.id}
                className={s.is_suspended ? 'operator-row--suspended' : ''}
              >
                <td>{s.id}</td>
                <td>{s.name}</td>
                <td><code>{s.slug}</code></td>
                <td>{s.owner_id}</td>
                <td>{s.member_count}</td>
                <td>
                  <span
                    className={`operator-badge ${
                      s.is_suspended
                        ? 'operator-badge--suspended'
                        : 'operator-badge--active'
                    }`}
                  >
                    {s.is_suspended ? 'SUSPENDED' : 'active'}
                  </span>
                </td>
                <td>{new Date(s.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="operator-section">
        <h2>
          Users <span className="operator-count">({users.length})</span>
        </h2>
        <table className="operator-table">
          <thead>
            <tr>
              <th>ID</th><th>Username</th><th>Email</th><th>Servers</th>
              <th>Status</th><th>Flags</th><th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr
                key={u.id}
                className={!u.is_active ? 'operator-row--disabled' : ''}
              >
                <td>{u.id}</td>
                <td>{u.username}</td>
                <td>{u.email}</td>
                <td>{u.server_count}</td>
                <td>
                  <span
                    className={`operator-badge ${
                      u.is_active
                        ? 'operator-badge--active'
                        : 'operator-badge--disabled'
                    }`}
                  >
                    {u.is_active ? 'active' : 'DISABLED'}
                  </span>
                </td>
                <td>
                  {u.is_site_admin && (
                    <span className="operator-flag">admin</span>
                  )}
                  {u.can_create_server && (
                    <span className="operator-flag">can-create</span>
                  )}
                </td>
                <td>{new Date(u.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
