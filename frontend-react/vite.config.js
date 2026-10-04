import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Talks to the FastAPI backend at http://127.0.0.1:8000
// Run backend separately (uvicorn main:app --reload) and this dev server (npm run dev).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
})
