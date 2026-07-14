import { defineConfig } from 'vite'
import path from 'path'
import fs from 'node:fs'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'


function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

/** Serve ../../promo/ directory at /promo/ path (concept slideshow & assets). */
function servePromo() {
  const promoDir = path.resolve(__dirname, '..', '..', 'promo')
  const MIME: Record<string, string> = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.webm': 'video/webm',
    '.mp4': 'video/mp4',
    '.mp3': 'audio/mpeg',
    '.ico': 'image/x-icon',
  }

  return {
    name: 'serve-promo',
    configureServer(server) {
      server.middlewares.use('/promo', (req, res, next) => {
        const urlPath = new URL(req.url!, `http://${req.headers.host}`).pathname
        const relative = urlPath.replace(/^\/promo\/?/, '')
        const filePath = path.join(promoDir, relative || 'concept/index.html')

        try {
          const stat = fs.statSync(filePath)
          if (stat.isDirectory()) {
            res.writeHead(302, { Location: urlPath.replace(/\/?$/, '/') + 'index.html' })
            res.end()
            return
          }
          const content = fs.readFileSync(filePath)
          const ext = path.extname(filePath).toLowerCase()
          res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream')
          res.end(content)
        } catch {
          next()
        }
      })
    },
  }
}

export default defineConfig(({ command }) => ({
  // In Electron production, assets must use relative paths (file:// protocol)
  base: command === "build" ? "./" : "/",
  plugins: [
    figmaAssetResolver(),
    servePromo(),
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // Alias @ to the src directory
      '@': path.resolve(__dirname, './src'),
    },
  },

  // Proxy API requests to the Chitrika backend
  server: {
    // IPv4 + 8080 avoids WinNAT/Hyper-V port reservation on Windows
    host: '127.0.0.1',
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
  assetsInclude: ['**/*.svg', '**/*.csv'],
}))
