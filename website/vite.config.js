import { defineConfig } from 'vite'

// Static build for any plain web host.
// base: './' => fully relative asset paths, so the dist/ folder works
// whether you drop it at the domain root or in a sub-folder.
export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2018',
    cssMinify: true,
    minify: 'esbuild',
    assetsInlineLimit: 4096,
    rollupOptions: {
      output: {
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
      },
    },
  },
  server: {
    port: 5173,
    open: true,
  },
})
