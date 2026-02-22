import api from './api'

export const getVapidPublicKey = () => api.get('/push/vapid-public-key')

export const subscribePush = (subscription) =>
  api.post('/push/subscribe', {
    endpoint: subscription.endpoint,
    keys: {
      p256dh: subscription.keys?.p256dh,
      auth: subscription.keys?.auth,
    },
  })

export const unsubscribePush = (endpoint) =>
  api.delete('/push/unsubscribe', { data: { endpoint } })
