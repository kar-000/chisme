import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Queue of callbacks waiting for an in-flight refresh to complete
let isRefreshing = false
let refreshQueue = []

function processQueue(error, token = null) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  refreshQueue = []
}

// On 401: silently refresh the access token using the refresh token.
// If no refresh token is stored, or if the refresh itself fails, clear
// auth state and redirect to the login page.
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config

    if (err.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(err)
    }

    const storedRefresh = localStorage.getItem('refresh_token')
    if (!storedRefresh) {
      localStorage.removeItem('token')
      window.location.href = '/'
      return Promise.reject(err)
    }

    // If a refresh is already in flight, queue this request to retry afterwards
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshQueue.push({ resolve, reject })
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      // Use raw axios (not `api`) to avoid triggering this interceptor again
      const { data } = await axios.post('/api/auth/refresh', {
        refresh_token: storedRefresh,
      })
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      processQueue(null, data.access_token)
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`
      return api(originalRequest)
    } catch (refreshErr) {
      processQueue(refreshErr)
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/'
      return Promise.reject(refreshErr)
    } finally {
      isRefreshing = false
    }
  },
)

export default api
