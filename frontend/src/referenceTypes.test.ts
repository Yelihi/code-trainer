import assert from 'node:assert/strict';
import { test } from 'node:test';
import { suggestionBlock, type NoteIssue } from './referenceTypes.ts';

test('only a unique source passage with a concrete replacement can be selected', () => {
  const issue: NoteIssue = { kind: 'correction_needed', quote: '**원문**', replacement: '**수정문**', explanation: '이유', suggestion: '안내' };
  assert.equal(suggestionBlock('앞 **원문** 뒤', issue), '');
  assert.match(suggestionBlock('다른 내용', issue), /위치/);
  assert.match(suggestionBlock('**원문** **원문**', issue), /위치/);
  assert.match(suggestionBlock('**원문**', { ...issue, replacement: undefined }), /이전 검토/);
  assert.match(suggestionBlock('**원문**', { ...issue, replacement: '' }), /추가 확인/);
  assert.match(suggestionBlock('**원문**', { ...issue, replacement: issue.quote }), /추가 확인/);
});
