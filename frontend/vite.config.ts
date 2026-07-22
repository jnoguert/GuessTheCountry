import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// VITE_BASE is set to '/Redactica/' by the GitHub Pages workflow;
// everywhere else the app is served from the root.
export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // The Easy Mode map chunk (react-simple-maps + world topology, ~860KB)
    // is intentionally large and lazy-loaded - only players who open it
    // download it, so the default 500KB warning is expected noise here.
    chunkSizeWarningLimit: 900,
  },
})
