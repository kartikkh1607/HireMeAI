import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Backend (FastAPI) ka address. Dev me Vite apne server (5173) pe UI chalata hai
// aur API calls ko yahan forward (proxy) kar deta hai -> browser ko lagta hai
// sab same origin se aa raha hai, isliye CORS ki zaroorat nahi.
const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/chat': BACKEND,
      '/profile': BACKEND,
      '/health': BACKEND,
    },
  },
  build: {
    // Production build seedha FastAPI ke static/ folder me jaata hai.
    // static/index.html + static/assets/* -> app/main.py inhe serve karta hai.
    outDir: '../static',
    emptyOutDir: true,
  },
})
