import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Ships Pyodide's runtime assets (wasm, stdlib zip, lock file) as static
    // files served from the same origin as the rest of the site — required
    // since GitHub Pages has no backend to proxy/host them elsewhere.
    viteStaticCopy({
      targets: [
        {
          src: [
            'node_modules/pyodide/pyodide.mjs',
            'node_modules/pyodide/pyodide.asm.mjs',
            'node_modules/pyodide/pyodide.asm.wasm',
            'node_modules/pyodide/python_stdlib.zip',
            'node_modules/pyodide/pyodide-lock.json',
          ],
          dest: 'pyodide',
          rename: { stripBase: true },
        },
      ],
    }),
  ],
  base: '/credit-card-bank-account-csv-summarizer/',
  // Pyodide is loaded and driven at runtime via loadPyodide(), not imported
  // as an ES module — esbuild's dev-time pre-bundling breaks its own
  // dynamic import/fetch of the wasm and stdlib assets above.
  optimizeDeps: { exclude: ['pyodide'] },
  server: {
    fs: {
      // multi_account_summarizer/ lives one level above dashboard/ (Vite's
      // project root) — pyEngine.js reads its .py sources via
      // import.meta.glob('../../../multi_account_summarizer/**/*.py', ...).
      allow: ['..'],
    },
  },
})
