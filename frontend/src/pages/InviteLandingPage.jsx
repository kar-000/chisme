import { useEffect, useState } from 'react'
import useAuthStore from '../store/authStore'
import { JoinServerModal } from '../components/Server/JoinServerModal'

/**
 * Handles /invite/{code} URLs.
 * Extracts the invite code from window.location.pathname (no react-router-dom).
 * If the user is not authenticated, stores the code in sessionStorage and
 * redirects to the login page; the auth flow should check for pendingInviteCode
 * after a successful login.
 */
export function InviteLandingPage() {
  const { token } = useAuthStore()
  const [showModal, setShowModal] = useState(false)

  // Extract the code from /invite/{code}
  const code = window.location.pathname.split('/').pop() ?? ''

  useEffect(() => {
    if (!token) {
      // Store the code so the post-login flow can resume
      if (code) sessionStorage.setItem('pendingInviteCode', code)
      // Redirect to root — the unauthenticated user will see the login page
      window.history.replaceState({}, '', '/')
      return
    }
    setShowModal(true)
  }, [token, code])

  const handleClose = () => {
    setShowModal(false)
    window.history.replaceState({}, '', '/')
  }

  if (!token) return null

  return showModal ? (
    <JoinServerModal initialCode={code} onClose={handleClose} />
  ) : null
}
