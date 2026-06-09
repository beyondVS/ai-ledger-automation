/// <reference types="vitest" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      }
    },
    watch: {
      usePolling: true,
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/components/__tests__/setup.js'],
  },
})
