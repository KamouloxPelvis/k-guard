import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(() => { 

  return {
    base: '/', 

    plugins: [vue()],
    
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        'crypto': 'crypto-js',
      }
    },

    server: {
      port: 30002,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        }
      }
    },

    define: {
      'global': 'window', 
    }
  }
})