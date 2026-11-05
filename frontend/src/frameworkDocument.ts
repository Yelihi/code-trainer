type PreviewMarkup = { html: string; css: string; client: string };

export function frameworkDocument(preview: PreviewMarkup, vendorSource: string) {
  const code = JSON.stringify(preview.client).replaceAll('<', '\\u003c');
  const vendor = JSON.stringify(vendorSource).replaceAll('<', '\\u003c');
  return `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' blob:; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"><style>body{margin:0;font-family:system-ui;color:#111;background:#fff}${preview.css}</style></head><body><div id="app">${preview.html}</div><script>
var exports = {}, module = { exports };
function require(name) { const value = window.trainerRuntime.modules[name]; if (!value) throw Error('지원하지 않는 모듈: ' + name); return value; }
function report(message) { parent.postMessage({ type: 'framework-preview-error', message: String(message) }, '*'); }
window.addEventListener('error', event => report(event.message));
function load(source, done) {
  const script = document.createElement('script');
  script.src = URL.createObjectURL(new Blob([source], { type: 'text/javascript' }));
  script.onload = () => { URL.revokeObjectURL(script.src); done(); };
  script.onerror = () => report('프레임워크 실행 코드를 불러오지 못했습니다.');
  document.body.appendChild(script);
}
load(${vendor}, () => load(${code}, () => {
  try { window.trainerRuntime.mount(module.exports.default); parent.postMessage({ type: 'framework-preview-ready' }, '*'); }
  catch (error) { report(error.message || error); }
}));
</script></body></html>`;
}
