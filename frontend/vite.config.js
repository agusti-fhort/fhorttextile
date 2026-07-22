import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://178.105.217.125',
        changeOrigin: true,
        headers: {
          Host: 'fhorttextile.tech'
        }
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // Framework core (react/router/http/i18n): ja s'executa eagerly a l'entry,
            // però abans anava tot dins del chunk "index" (>500kB). Es separa a part
            // perquè sigui cacheable i no compti com a chunk d'APP; la resta de
            // node_modules (dnd-kit, @svar-ui, tabler-icons, etc.) es queda amb el
            // xunkejament automàtic per no perdre el seu lazy-load per pàgina.
            if (/\/(react|react-dom|react-router|react-router-dom|scheduler|use-sync-external-store|axios|i18next|i18next-browser-languagedetector|react-i18next|zustand)\//.test(id)) {
              return 'vendor-react'
            }
            // NO forçar cap chunk per a konva. Hi havia un `vendor-konva` explícit i era
            // contraproduent: agrupar konva + react-konva a la força hi arrossegava el pont
            // de react-konva cap a React, i l'entry acabava important-ne un símbol de manera
            // ESTÀTICA. Resultat: els 317 kB de Konva al `modulepreload` de l'index.html de
            // TOTES les pàgines, quan només el fan servir les de canvas (§B4.4, punt 6) —
            // i els 44 `lazy(() => import(...))` d'App.jsx no en podien fer res.
            // Amb el xunkejament automàtic, Konva queda igual de junt (306 kB en un sol
            // chunk) però NOMÉS com a dependència dinàmica de les pàgines que l'importen.
            // Càrrega inicial: 1.112.390 B → 806.529 B.
            //
            // Els dos que queden van ancorats a `node_modules/<nom>/` a propòsit: amb un
            // `includes()` solt, qualsevol paquet que dugués la paraula al camí hi cauria.
            if (/node_modules\/paper\//.test(id)) return 'vendor-paper'
            if (/node_modules\/pdf-lib\//.test(id)) return 'vendor-pdf'
          }
        },
      },
    },
  },
})
