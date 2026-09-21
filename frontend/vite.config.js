import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'fs'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: true,
    port: 2001,
    allowedHosts: ['localhost', '127.0.0.1', '192.168.0.7'],
    https: {
      key: fs.readFileSync(path.resolve(import.meta.dirname, '../backend/key.pem')),
      cert: fs.readFileSync(path.resolve(import.meta.dirname, '../backend/cert.pem')),
    }
  },
  preview: {
    host: true,
    port: 2001,
    allowedHosts: ['localhost', '127.0.0.1', '192.168.0.7'],
    https: {
      key: fs.readFileSync(path.resolve(import.meta.dirname, '../backend/key.pem')),
      cert: fs.readFileSync(path.resolve(import.meta.dirname, '../backend/cert.pem')),
    }
  }
})
