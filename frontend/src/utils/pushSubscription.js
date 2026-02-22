/**
 * Web Push subscription helpers.
 *
 * Usage:
 *   await registerPushIfAvailable()  // call after notification permission is granted
 */

import { subscribePush, unsubscribePush, getVapidPublicKey } from '../services/push'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)))
}

export async function registerPushIfAvailable() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return
  if (Notification.permission !== 'granted') return

  try {
    const { data } = await getVapidPublicKey()
    const vapidPublicKey = data?.key
    if (!vapidPublicKey) return // VAPID not configured on server

    const registration = await navigator.serviceWorker.ready
    const existing = await registration.pushManager.getSubscription()
    if (existing) {
      // Already subscribed — ensure the server knows about it
      await subscribePush(existing.toJSON())
      return
    }

    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    })
    await subscribePush(subscription.toJSON())
  } catch {
    // Push registration is best-effort — silent failure is fine
  }
}

export async function unregisterPush() {
  if (!('serviceWorker' in navigator)) return
  try {
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()
    if (subscription) {
      await unsubscribePush(subscription.endpoint)
      await subscription.unsubscribe()
    }
  } catch {
    // Silent
  }
}
