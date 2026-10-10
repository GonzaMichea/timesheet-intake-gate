import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Solo para iterar en local sin `vercel dev`: reenvía /api al backend en el puerto 8000
  server: { proxy: { "/api": "http://localhost:8000" } },
})
