import { type CompletionSource } from '@codemirror/autocomplete';
import { completionPath, scopeCompletionSource } from '@codemirror/lang-javascript';

const globals = scopeCompletionSource({
  Array, Object, String, Number, Boolean, Map, Set, Date, Promise, Math, JSON,
  parseInt, parseFloat, isNaN, isFinite,
  console: { log: console.log, error: console.error, warn: console.warn },
});

const instances = {
  Array: Array.prototype,
  String: String.prototype,
  Map: Map.prototype,
  Set: Set.prototype,
  Date: Date.prototype,
  Number: Number.prototype,
};
type Instance = keyof typeof instances;

function instanceType(annotation: string, initializer = ''): Instance | undefined {
  if (/\[\]|\bArray\s*</.test(annotation) || /^\s*(?:\[|Array\.(?:from|of)\s*\()/.test(initializer)) return 'Array';
  if (/\bstring\b/i.test(annotation) || /^\s*['"`]/.test(initializer)) return 'String';
  if (/\bMap\s*</.test(annotation) || /^\s*new\s+Map\b/.test(initializer)) return 'Map';
  if (/\bSet\s*</.test(annotation) || /^\s*new\s+Set\b/.test(initializer)) return 'Set';
  if (/\bDate\b/.test(annotation) || /^\s*new\s+Date\b/.test(initializer)) return 'Date';
  if (/\bnumber\b/i.test(annotation) || /^\s*-?\d/.test(initializer)) return 'Number';
}

function declaredType(source: string, name: string): Instance | undefined {
  let kind: Instance | undefined;
  // shortcut: Infer explicit types and simple initializers only; use a language service for expression-level types.
  for (const match of source.matchAll(/\b(?:const|let|var)\s+([\w$]+)\s*(?::\s*([^=\n]+))?\s*=\s*([^;\n]+)/g)) {
    if (match[1] === name) kind = instanceType(match[2] ?? '', match[3]);
  }
  if (kind) return kind;
  for (const match of source.matchAll(/\b([\w$]+)\s*:\s*((?:readonly\s+)?(?:\w+\[\]|Array<[^>]+>|Map<[^>]+>|Set<[^>]+>|string|number|Date))/g)) {
    if (match[1] === name) kind = instanceType(match[2]);
  }
  return kind;
}

export const standardApiCompletions: CompletionSource = context => {
  const globalResult = globals(context);
  if (globalResult) return globalResult;
  const path = completionPath(context);
  if (path?.path.length !== 1) return null;
  const kind = declaredType(context.state.doc.sliceString(0, context.pos), path.path[0]);
  if (!kind) return null;
  const options = Object.entries(Object.getOwnPropertyDescriptors(instances[kind]))
    .filter(([name]) => name !== 'constructor' && !name.startsWith('__'))
    .map(([label, descriptor]) => ({ label, type: typeof descriptor.value === 'function' ? 'method' : 'property', detail: kind }));
  return { from: context.pos - path.name.length, options, validFor: /^[\w$]*$/ };
};
