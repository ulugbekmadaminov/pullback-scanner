import { defineConfig, type Plugin } from "vite";
import { readFileSync, writeFileSync } from "node:fs";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8"));

// public/ ichidagi qobiq fayllari (data/ emas — u alohida, tarmoq-birinchi keshlanadi)
const PUBLIC_SHELL = ["./theme.js", "./manifest.webmanifest", "./icons/icon-192.png", "./icons/icon-512.png", "./icons/maskable-512.png", "./icons/apple-touch-icon.png"];

// Service worker build paytida yoziladi: kesh nomi versiyadan olinadi (unutilmasligi uchun)
// va ilova qobig'idagi barcha fayllar oldindan keshlanadi.
function serviceWorker(): Plugin {
  let outDir = "dist";
  const assets: string[] = [];
  return {
    name: "saralash-sw",
    apply: "build",
    configResolved(c) { outDir = c.build.outDir; },
    generateBundle(_o, bundle) { for (const f of Object.keys(bundle)) assets.push(f); },
    closeBundle() {
      const src = readFileSync(new URL("./src/sw.template.js", import.meta.url), "utf8")
        .replace("__VERSION__", pkg.version + "-" + Date.now().toString(36))
        .replace("__ASSETS__", JSON.stringify(["./", ...PUBLIC_SHELL, ...assets.map((a) => "./" + a)]));
      writeFileSync(`${outDir}/sw.js`, src);
    },
  };
}

export default defineConfig({
  base: process.env.VITE_BASE || "./",
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  // assetsInlineLimit: 0 - shriftlar data: URI bo'lib qolmasin (CSP font-src 'self')
  build: { target: "es2021", chunkSizeWarningLimit: 700, assetsInlineLimit: 0 },
  plugins: [serviceWorker()],
});
