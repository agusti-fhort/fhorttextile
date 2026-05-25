import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://178.105.217.125',
        changeOrigin: true,
        headers: {
          Host: 'fhorttextile.tech'
        }
      }
    }
  }
})
