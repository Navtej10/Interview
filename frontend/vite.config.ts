import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        {
          src: 'node_modules/@ricky0123/vad-web/dist/vad.worklet.bundle.min.js',
          dest: ''
        },
        {
          src: 'node_modules/@ricky0123/vad-web/dist/*.onnx',
          dest: ''
        },
        {
          src: 'node_modules/onnxruntime-web/dist/*.wasm',
          dest: ''
        },
        {
          src: 'node_modules/onnxruntime-web/dist/*.mjs',
          dest: ''
        },
        {
          src: 'node_modules/onnxruntime-web/dist/*.mjs',
          dest: 'node_modules/.vite/deps'
        }
      ]
    })
  ],
  server: { port: 5173 },
})
