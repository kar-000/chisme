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

export async function showNotification(title, { body, tag, onClick } = {}) {
  if (Notification.permission !== 'granted') return

  // Prefer SW registration.showNotification() — required for reliable PWA
  // notifications. new Notification() is silently blocked by Chrome when the
  // page is not in the foreground or when running as an installed PWA.
  if ('serviceWorker' in navigator) {
    try {
      const reg = await navigator.serviceWorker.getRegistration()
      if (reg) {
        await reg.showNotification(title, {
          body,
          tag,
          icon: '/icons/notif1.png',
          badge: '/icons/badge-72.png',
          renotify: false,
        })
        return
      }
    } catch {
      // Fall through to legacy path
    }
  }

  // Fallback for dev environments without a service worker
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
