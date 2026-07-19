import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// VITE_BASE is set to '/GuessTheCountry/' by the GitHub Pages workflow;
// everywhere else the app is served from the root.
export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
