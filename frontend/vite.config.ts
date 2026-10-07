import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev contre le LXC : VITE_API_URL=https://192.168.10.39:8000 npm run dev
    // (sinon proxy local vers l'API sur localhost:8000)
    proxy: { '/api': process.env.VITE_API_URL || 'https://localhost:8000' },
  },
  build: { outDir: 'dist' }
})
