/**
 * Browser notification helpers.
 *
 * Usage:
 *   await requestNotificationPermission()   // call once on login
 *   showNotification('New message', { body: 'Hello!', onClick: () => {} })
 */

import { registerPushIfAvailable } from './pushSubscription'

export async function requestNotificationPermission() {
  if (!('Notification' in window)) return false
  if (Notification.permission === 'granted') {
    await registerPushIfAvailable()
    return true
  }
  if (Notification.permission === 'denied') return false
  const result = await Notification.requestPermission()
  if (result === 'granted') {
    await registerPushIfAvailable()
    return true
  }
  return false
}

export function showNotification(title, { body, tag, onClick } = {}) {
  if (Notification.permission !== 'granted') return
  if (document.hasFocus()) return // don't spam when user is looking at the tab

  const n = new Notification(title, {
    body,
    tag,
    icon: '/favicon.ico',
    badge: '/favicon.ico',
  })

  n.onclick = () => {
    window.focus()
    n.close()
    onClick?.()
  }

  // Auto-close after 8s
  setTimeout(() => n.close(), 8000)
}

/**
 * Check if a message content @-mentions the given username.
 */
export function isMention(content, username) {
  if (!content || !username) return false
  return content.toLowerCase().includes(`@${username.toLowerCase()}`)
}
