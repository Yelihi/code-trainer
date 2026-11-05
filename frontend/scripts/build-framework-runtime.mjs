import { build } from 'esbuild';
import { mkdir } from 'node:fs/promises';
import { URL } from 'node:url';

await mkdir(new URL('../public/framework-runtime/', import.meta.url), { recursive: true });
for (const framework of ['react', 'vue']) {
  await build({
    entryPoints: [new URL(`../framework-runtime/${framework}-entry.ts`, import.meta.url).pathname],
    outfile: new URL(`../public/framework-runtime/${framework}-v1.js`, import.meta.url).pathname,
    bundle: true, minify: true, format: 'iife', platform: 'browser', target: 'es2022',
  });
}
