/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: false,         // We manage manifest.json ourselves in public/
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.js',
      injectManifest: {
        injectionPoint: undefined, // don't inject precache manifest into sw
      },
    }),
  ],
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
      '/uploads': 'http://localhost:8100',
      '/ws': { target: 'ws://localhost:8100', ws: true },
    },
  },
})
