import { useState, useEffect, useRef } from 'react'
import { CreateServerModal } from './CreateServerModal'
import { JoinServerModal } from './JoinServerModal'

export function AddServerButton() {
  const [showMenu, setShowMenu] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [showJoin, setShowJoin] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!showMenu) return
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showMenu])

  return (
    <div ref={containerRef}>
      <button
        className="server-icon server-icon--add"
        title="Add a server"
        onClick={() => setShowMenu((v) => !v)}
        type="button"
      >
        +
      </button>

      {showMenu && (
        <div className="server-add-menu">
          <button
            className="server-add-menu__item"
            onClick={() => { setShowCreate(true); setShowMenu(false) }}
            type="button"
          >
            Create a Server
          </button>
          <button
            className="server-add-menu__item"
            onClick={() => { setShowJoin(true); setShowMenu(false) }}
            type="button"
          >
            Join a Server
          </button>
        </div>
      )}

      {showCreate && <CreateServerModal onClose={() => setShowCreate(false)} />}
      {showJoin && <JoinServerModal onClose={() => setShowJoin(false)} />}
    </div>
  )
}
