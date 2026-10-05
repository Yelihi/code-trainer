// Named TypeScript/JavaScript functions and event registrations; no application execution.
import ts from '../../frontend/node_modules/typescript/lib/typescript.js';
import { execFileSync } from 'node:child_process';
const files = execFileSync('git', ['ls-files', '-z'], { encoding: 'utf8' }).split('\0')
  .filter(f => /^(frontend\/src\/|deploy\/cloudflare\/)/.test(f) && /\.(tsx?|mjs)$/.test(f) && !/\.test\./.test(f));
const program = ts.createProgram(files, { allowJs: true, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ESNext, moduleResolution: ts.ModuleResolutionKind.Bundler, module: ts.ModuleKind.ESNext });
const checker = program.getTypeChecker();
const records = [], declarations = new Map();
const compact = n => n?.getText().replace(/\s+/g, ' ').slice(0, 200) ?? '';
for (const file of files) {
  const source = program.getSourceFile(file);
  function collect(node, parents = []) {
    let name;
    if (ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || ts.isConstructorDeclaration(node)) name = node.name?.getText(source) || (ts.isConstructorDeclaration(node) ? 'constructor' : undefined);
    if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
      const p = node.parent;
      if (ts.isVariableDeclaration(p) || ts.isPropertyAssignment(p)) name = p.name.getText(source);
      else if (ts.isCallExpression(p) && ts.isVariableDeclaration(p.parent)) name = p.parent.name.getText(source);
    }
    if (name) {
      const qualified = [...parents, name].join('.');
      const line = source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1;
      const record = { id: `${file}::${qualified}`, path: file, name: qualified, line,
        end: source.getLineAndCharacterOfPosition(node.end).line + 1, calls: [], events: [], node };
      records.push(record); declarations.set(node, record);
      if (ts.isVariableDeclaration(node.parent)) declarations.set(node.parent, record);
      if (ts.isCallExpression(node.parent) && ts.isVariableDeclaration(node.parent.parent)) declarations.set(node.parent.parent, record);
      ts.forEachChild(node, child => collect(child, [...parents, name]));
    } else {
      const next = ts.isClassDeclaration(node) && node.name ? [...parents, node.name.text] : parents;
      ts.forEachChild(node, child => collect(child, next));
    }
  }
  collect(source);
}
for (const record of records) {
  function walk(node) {
    if (node !== record.node && declarations.has(node)) return;
    if (ts.isCallExpression(node)) {
      let symbol = checker.getSymbolAtLocation(ts.isPropertyAccessExpression(node.expression) ? node.expression.name : node.expression);
      if (symbol?.flags & ts.SymbolFlags.Alias) symbol = checker.getAliasedSymbol(symbol);
      const target = symbol?.declarations?.map(d => declarations.get(d)).find(Boolean);
      record.calls.push({ name: compact(node.expression), ...(target ? { target: target.id } : {}) });
      const name = compact(node.expression);
      if (['api', 'fetch', 'useEffect', 'setInterval', 'setTimeout'].includes(name) || /\.(addEventListener|dispatchEvent)$/.test(name)) {
        let event = name;
        if (name === 'api') event = `HTTP ${node.arguments[1] ? compact(node.arguments[1]) : 'GET'} ${compact(node.arguments[0])} (접두사 /api)`;
        else if (name === 'setInterval' || name === 'setTimeout') event += ` · ${compact(node.arguments[1])} ms`;
        else if (name !== 'useEffect') event += ` · ${compact(node.arguments[0])}`;
        else event += ' · 마운트/의존성 변경, 반환된 cleanup 실행';
        record.events.push(event);
      }
    }
    if (ts.isJsxAttribute(node) && /^on[A-Z]/.test(node.name.getText())) record.events.push(`${node.name.getText()} → ${compact(node.initializer)}`);
    ts.forEachChild(node, walk);
  }
  walk(record.node);
  record.calls = [...new Map(record.calls.map(c => [c.name + (c.target || ''), c])).values()];
  record.events = [...new Set(record.events)];
  delete record.node;
}
process.stdout.write(JSON.stringify(records));
