// Small structural diagrams, kept decorative so card names remain the accessible labels.
const drawings: Record<string, { outline: string; accent: string }> = {
  stack: { outline: 'M42 18v90h76V18 M50 80h60v20H50z M50 54h60v20H50z', accent: 'M50 28h60v20H50z M80 4v16m-5-5 5 5 5-5' },
  queue: { outline: 'M14 40h132 M14 85h132 M50 49h24v27H50z M82 49h24v27H82z M114 49h24v27h-24z', accent: 'M18 49h24v27H18z M8 62H0m5-5-5 5 5 5 M148 62h12m-5-5 5 5-5 5' },
  'linked-list': { outline: 'M4 20h40v32H4z M17 20v32 M104 20h40v32h-40z M117 20v32 M54 84h40v32H54z M67 84v32', accent: 'M32 36h66m-6-5 6 5-6 5 M134 52v48h-34m6-5-6 5 6 5' },
  dictionary: { outline: 'M10 16h44v24H10z M10 52h44v24H10z M10 88h44v24H10z M110 28h40v24h-40z M110 82h40v24h-40z', accent: 'M54 28h26l30 12 M54 64h26l30-24 M54 100h26l30-6 M74 23v46' },
  'priority-queue': { outline: 'M80 26 40 62 20 104 M40 62l20 42 M80 26l40 36-20 42 M120 62l20 42 M30 62a10 10 0 1 0 20 0a10 10 0 1 0-20 0 M110 62a10 10 0 1 0 20 0a10 10 0 1 0-20 0', accent: 'M68 22a12 12 0 1 0 24 0a12 12 0 1 0-24 0 M14 104h12 M54 104h12 M94 104h12 M134 104h12' },
  'binary-search': { outline: 'M4 48h152v30H4z M29 48v30 M54 48v30 M80 48v30 M105 48v30 M130 48v30 M4 90h76', accent: 'M54 48h26v30H54z M67 16v24m-6-6 6 6 6-6 M4 84v12 M80 84v12' },
  'merge-sort': { outline: 'M10 15h60v20H10z M90 15h60v20H90z M40 35 20 60 M40 35l20 25 M120 35 100 60 M120 35l20 25 M10 60h20v18H10z M50 60h20v18H50z M90 60h20v18H90z M130 60h20v18h-20z', accent: 'M20 78 50 100 M60 78l10 22 M100 78 90 100 M140 78l-30 22 M40 102h80v18H40z M60 102v18 M80 102v18 M100 102v18' },
  bfs: { outline: 'M18 62 62 20 110 34 142 84 76 106 18 62 M62 20l14 86 M110 34 18 62 M110 34 76 106', accent: 'M8 62a10 10 0 1 0 20 0a10 10 0 1 0-20 0 M52 20a10 10 0 1 0 20 0a10 10 0 1 0-20 0 M100 34a10 10 0 1 0 20 0a10 10 0 1 0-20 0 M66 106a10 10 0 1 0 20 0a10 10 0 1 0-20 0' },
  dfs: { outline: 'M18 62 62 20 110 34 142 84 76 106 18 62 M62 20l14 86 M110 34 18 62 M110 34 76 106', accent: 'M18 62 62 20 110 34 142 84 76 106 M8 62a10 10 0 1 0 20 0a10 10 0 1 0-20 0 M132 84a10 10 0 1 0 20 0a10 10 0 1 0-20 0' },
  map: { outline: 'M12 14h28v22H12z M66 14h28v22H66z M120 14h28v22h-28z M26 42v28 M80 42v28 M134 42v28', accent: 'M12 80h28v32H12z M66 80h28v32H66z M120 80h28v32h-28z M20 64l6 6 6-6 M74 64l6 6 6-6 M128 64l6 6 6-6' },
  filter: { outline: 'M12 14h28v22H12z M66 14h28v22H66z M120 14h28v22h-28z M76 52l8 8 M84 52l-8 8', accent: 'M26 42 50 78 M134 42 110 78 M36 86h28v26H36z M96 86h28v26H96z' },
  reduce: { outline: 'M12 14h28v22H12z M66 14h28v22H66z M120 14h28v22h-28z M26 42 80 80 M80 42v38 M134 42 80 80', accent: 'M62 84h36v30H62z M80 90v18 M71 99h18' },
};

export function FoundationCardArt({ kind }: { kind: string }) {
  const drawing = drawings[kind];
  return drawing && <svg className="foundation-card-art" viewBox="0 0 160 128" aria-hidden="true" focusable="false"><path d={drawing.outline} /><path className="card-art-accent" d={drawing.accent} /></svg>;
}
