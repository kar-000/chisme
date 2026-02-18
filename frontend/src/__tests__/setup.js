import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

// WebSocket mock
class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = MockWebSocket.CONNECTING
    this.sent = []
    MockWebSocket._instances.push(this)
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.()
    }, 0)
  }
  send(data) {
    this.sent.push(data)
  }
  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }
}
MockWebSocket.CONNECTING = 0
MockWebSocket.OPEN = 1
MockWebSocket.CLOSING = 2
MockWebSocket.CLOSED = 3
MockWebSocket._instances = []

global.WebSocket = MockWebSocket

// localStorage mock (jsdom provides it, but reset between tests)
beforeEach(() => {
  localStorage.clear()
  MockWebSocket._instances = []
})

// Suppress noisy console.error from React prop warnings in tests
vi.spyOn(console, 'error').mockImplementation(() => {})
