/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.js'],
    globals: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['src/main.jsx', 'src/__tests__/**'],
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8100',
      '/ws': { target: 'ws://localhost:8100', ws: true },
    },
  },
})
