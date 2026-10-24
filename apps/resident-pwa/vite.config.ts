import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // docs/04 §16: manifest named SocietyIQ, brand icons, theme colour teal.
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.ico", "apple-touch-icon-180x180.png", "logo-light.svg", "mark.svg"],
      manifest: {
        name: "SocietyIQ",
        short_name: "SocietyIQ",
        description: "SocietyIQ resident app",
        theme_color: "#2E6B5E",
        background_color: "#F7F6F2",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "pwa-64x64.png", sizes: "64x64", type: "image/png" },
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          { src: "maskable-icon-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2}"],
        navigateFallback: "/index.html",
        // docs/04 §16: keep the last-loaded dues, bills, receipts and notices for offline
        // reading. Network first, so online the data is always fresh.
        runtimeCaching: [
          {
            urlPattern: ({ url, request }) =>
              request.method === "GET" && /\/api\/v1\/societies\/[^/]+\/(my\/flats|notices)/.test(url.pathname),
            handler: "NetworkFirst",
            options: {
              cacheName: "resident-data",
              networkTimeoutSeconds: 6,
              expiration: { maxEntries: 60, maxAgeSeconds: 30 * 24 * 60 * 60 },
            },
          },
        ],
      },
    }),
  ],
  test: { environment: "jsdom", setupFiles: ["./src/test-setup.ts"] },
});
