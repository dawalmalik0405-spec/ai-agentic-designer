import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/assets": "http://localhost:8000",
      "/generated-assets": "http://localhost:8000",
      "/generated-preview": "http://localhost:8000",
    },
  },
})
