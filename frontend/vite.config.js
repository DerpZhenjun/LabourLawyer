import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// 手动定义 __dirname (兼容 ESM 环境)
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig({
  plugins: [vue()],
  server: {
    fs: { allow: [__dirname, path.resolve(__dirname, '../config'), path.resolve(__dirname, '../packages/regional-contracts')] }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
