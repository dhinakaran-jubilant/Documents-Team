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
    {
      name: 'restrict-ips',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const remoteAddress = req.socket.remoteAddress || '';
          const clientIp = remoteAddress.replace(/^::ffff:/, '');
          const allowedIps = ['127.0.0.1', '::1', 'localhost', '192.168.0.7'];
          if (!allowedIps.includes(clientIp) && !allowedIps.includes(remoteAddress)) {
            res.statusCode = 403;
            res.setHeader('Content-Type', 'text/plain');
            res.end('Forbidden: Access is allowed only from localhost and 192.168.0.7');
            return;
          }
          next();
        });
      }
    }
  ],
  server: {
    host: true,
    port: 2001,
    allowedHosts: ['localhost', '127.0.0.1', '192.168.0.7'],
    https: {
      key: fs.readFileSync(path.resolve(__dirname, '../backend/key.pem')),
      cert: fs.readFileSync(path.resolve(__dirname, '../backend/cert.pem')),
    }
  }
})
