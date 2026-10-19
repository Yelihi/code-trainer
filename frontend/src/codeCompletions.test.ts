import assert from 'node:assert/strict';
import test from 'node:test';
import { CompletionContext } from '@codemirror/autocomplete';
import { javascript } from '@codemirror/lang-javascript';
import { EditorState } from '@codemirror/state';
import { standardApiCompletions } from './codeCompletions.ts';

async function labels(code: string) {
  const state = EditorState.create({ doc: code, extensions: [javascript({ typescript: true })] });
  const result = await standardApiCompletions(new CompletionContext(state, code.length, false));
  return result?.options.map(option => option.label) ?? [];
}

test('standard API suggestions follow common local types without leaking unrelated methods', async () => {
  assert((await labels('const values = [1, 2]; values.')).includes('map'));
  assert(!(await labels('const values = [1, 2]; values.')).includes('get'));
  assert((await labels('function show(items: string[]) { items.')).includes('filter'));
  assert((await labels('const lookup = new Map(); lookup.')).includes('get'));
  assert((await labels('const title = "hello"; title.')).includes('slice'));
  assert((await labels('Math.')).includes('max'));
  assert.deepEqual(await labels('const unknown = makeValue(); unknown.'), []);
  assert.deepEqual(await labels('// Math.'), []);
});
