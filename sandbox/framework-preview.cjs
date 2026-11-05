const fs = require('node:fs');
const Module = require('node:module');
const ts = require('typescript');

function compile(source) {
  return ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } }).outputText;
}

function load(js, filename) {
  const compiled = new Module(filename, module);
  compiled.filename = filename;
  compiled.paths = Module._nodeModulePaths('/work');
  compiled._compile(js, filename);
  return compiled.exports.default;
}

async function main() {
  console.log = (...values) => process.stderr.write(values.join(' ') + '\n');
  const [framework, filename] = process.argv.slice(2);
  const source = fs.readFileSync(filename, 'utf8');
  let html = '', css = '', client;
  if (framework === 'react') {
    const React = require('react');
    const { renderToStaticMarkup } = require('react-dom/server');
    client = compile(source);
    try {
      const App = load(client, filename);
      if (typeof App !== 'function') throw new Error('React 코드는 App 컴포넌트를 기본 내보내기로 작성해주세요.');
      html = renderToStaticMarkup(React.createElement(App));
    } catch (error) { process.stderr.write('서버 렌더링 건너뜀: ' + String(error.message || error)); }
  } else if (framework === 'vue') {
    const { parse, compileScript, compileTemplate } = require('@vue/compiler-sfc');
    const { createSSRApp } = require('vue');
    const { renderToString } = require('vue/server-renderer');
    const parsed = parse(source, { filename });
    if (parsed.errors.length || !parsed.descriptor.template) throw new Error('Vue 단일 파일 컴포넌트의 <template>을 확인해주세요.');
    const { descriptor } = parsed;
    const compiledScript = descriptor.script || descriptor.scriptSetup ? compileScript(descriptor, { id: 'practice' }) : null;
    const script = compiledScript?.content ?? 'export default {}';
    const template = compileTemplate({ source: descriptor.template.content, filename, id: 'practice',
      compilerOptions: { bindingMetadata: compiledScript?.bindings } });
    if (template.errors.length) throw new Error(String(template.errors[0]));
    client = compile(`${script}\n${template.code}\nexports.default.render = exports.render;`);
    try { html = await renderToString(createSSRApp(load(client, filename))); }
    catch (error) { process.stderr.write('서버 렌더링 건너뜀: ' + String(error.message || error)); }
    css = descriptor.styles.filter(style => !style.src).map(style => style.content).join('\n');
  } else {
    throw new Error('지원하지 않는 프레임워크입니다.');
  }
  process.stdout.write(JSON.stringify({ html, css, client }));
}

main().catch(error => { process.stderr.write(String(error.message || error)); process.exitCode = 1; });
