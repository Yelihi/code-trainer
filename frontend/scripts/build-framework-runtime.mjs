import { build } from 'esbuild';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath, URL } from 'node:url';

const local = path => fileURLToPath(new URL(path, import.meta.url));
await mkdir(local('../public/framework-runtime/'), { recursive: true });
for (const framework of ['react', 'vue']) {
  await build({
    entryPoints: [local(`../framework-runtime/${framework}-entry.ts`)],
    outfile: local(`../public/framework-runtime/${framework}-v1.js`),
    bundle: true, minify: true, format: 'iife', platform: 'browser', target: 'es2022',
  });
}
