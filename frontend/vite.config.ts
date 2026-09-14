import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            // Ignore connection resets and aborts when browser tabs close or reload
            if ((err as any).code === 'ECONNABORTED' || (err as any).code === 'ECONNRESET') {
              return;
            }
          });
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
