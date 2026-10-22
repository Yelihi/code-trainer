import assert from 'node:assert/strict';
import { test } from 'node:test';
import { registrationBlock, suggestionBlock, type NoteIssue, type Proposal } from './referenceTypes.ts';

test('registration explains review blockers independently of concept confirmation', () => {
  const proposal: Proposal = { id: 'p', revision: 1, state: 'ready', error: '', data: null, review: { summary: '검토', issues: [] } };
  assert.equal(registrationBlock('', null, 1), '');
  assert.match(registrationBlock('p', null, 1), /불러오는 중/);
  assert.equal(registrationBlock('p', proposal, 1), '');
  assert.match(registrationBlock('p', { ...proposal, state: 'running' }, 1), /검토 중/);
  assert.match(registrationBlock('p', { ...proposal, state: 'failed' }, 1), /실패/);
  assert.match(registrationBlock('p', proposal, 2), /본문이 변경/);
  assert.match(registrationBlock('p', { ...proposal, review: null }, 1), /검토 전/);
  assert.match(registrationBlock('p', { ...proposal, review: { summary: '수정 필요', issues: [{} as NoteIssue] } }, 1), /1개가 남아/);
});

test('only a unique source passage with a concrete replacement can be selected', () => {
  const issue: NoteIssue = { kind: 'correction_needed', quote: '**원문**', replacement: '**수정문**', explanation: '이유', suggestion: '안내' };
  assert.equal(suggestionBlock('앞 **원문** 뒤', issue), '');
  assert.match(suggestionBlock('다른 내용', issue), /위치/);
  assert.match(suggestionBlock('**원문** **원문**', issue), /위치/);
  assert.match(suggestionBlock('**원문**', { ...issue, replacement: undefined }), /이전 검토/);
  assert.match(suggestionBlock('**원문**', { ...issue, replacement: '' }), /추가 확인/);
  assert.match(suggestionBlock('**원문**', { ...issue, replacement: issue.quote }), /추가 확인/);
});
