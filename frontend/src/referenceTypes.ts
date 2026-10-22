export type ReferenceMetadata = { kind: 'book' | 'lecture' | 'article' | 'experience' | 'other'; title: string; author: string; url: string; locator: string };
export const referenceKinds = { book: '책', lecture: '강의', article: '글 · 아티클', experience: '직접 경험', other: '기타' };
export const relations = { CLAIM: '주장', PREREQUISITE_OF: '선행 개념 → 후속 개념', BROADER_THAN: '상위 개념 → 하위 개념', USED_IN: '개념 → 활용 대상', RELATED_TO: '연관 개념 ↔ 개념' };
export const bases = { source: '출처에서 정리한 내용', interpretation: '나의 해석', question: '아직 풀리지 않은 질문' };
export type Concept = { id: string; pref_label: string; definition: string; scope: string; aliases: string[]; status: string };
export type ConceptMatch = { key?: string; concept: Concept; reason: string };
export type Candidate = { key: string; existing_id: string; pref_label: string; definition: string; scope: string; aliases: string[]; quote: string; basis: keyof typeof bases };
export type Assertion = { subject: string; kind: keyof typeof relations; object: string; text: string; scope: string; quote: string; basis: keyof typeof bases; disposition: 'supports' | 'refutes' };
export type ProposalData = { concepts: Candidate[]; assertions: Assertion[] };
export type NoteIssue = { kind: 'correction_needed' | 'needs_verification'; quote: string; explanation: string; suggestion: string; replacement?: string };
export type NoteContentReview = { summary: string; issues: NoteIssue[] };
export type Proposal = { id: string; revision: number; state: string; data: ProposalData | null; review: NoteContentReview | null; matches?: ConceptMatch[]; error: string };
export type ReferenceNote = { id: string; title: string; body: string; metadata: ReferenceMetadata; revision: number; archived: number; updated_at: string;
  registration: { id: string; version: number; state: string; created_at: string } | null;
  versions: { revision: number; created_at: string }[]; reviews: { id: string; state: string; created_at: string }[];
  proposal: { id: string; state: string; revision: number } | null };
export type ReviewSource = { id: string; note_id: string | null; title: string; version: number; body: string; metadata: ReferenceMetadata; relationship: string };
export type ReviewTurn = { role: 'user'; answer: string; request_id: string } | { role: 'assistant'; feedback: string; question: string; citations: string[] };
export type ReferenceReview = { id: string; note_id: string; revision: number; state: string; error: string; turns: ReviewTurn[]; sources: ReviewSource[] };
export const newReferenceId = () => crypto.randomUUID().replaceAll('-', '');
export function suggestionBlock(body: string, issue: NoteIssue) {
  if (issue.replacement === undefined) return '이전 검토에는 교체 문장이 없습니다. AI로 후보 생성·내용 검토를 다시 진행해주세요.';
  if (!issue.replacement.trim() || issue.replacement === issue.quote) return '추가 확인이 필요한 항목입니다. 안내를 확인한 뒤 본문에서 직접 수정해주세요.';
  const start = body.indexOf(issue.quote);
  if (!issue.quote || start < 0 || body.indexOf(issue.quote, start + 1) >= 0) return '원문 위치를 하나로 정할 수 없습니다. 본문에서 직접 수정해주세요.';
  return '';
}
export function registrationBlock(proposalId: string, proposal: Proposal | null, revision: number) {
  if (!proposalId) return '';
  if (!proposal) return 'AI 검토 결과를 불러오는 중입니다. 불러오지 못하면 페이지를 새로고침해주세요.';
  if (proposal.state === 'running') return 'AI가 본문과 후보를 검토 중입니다. 완료되면 등록할 수 있습니다.';
  if (proposal.revision !== revision) return '본문이 변경되어 이전 검토를 사용할 수 없습니다. 새 본문에서 AI 후보 생성·내용 검토를 다시 진행해주세요.';
  if (proposal.state === 'failed') return 'AI 검토가 실패해 등록할 수 없습니다. 위 오류를 확인한 뒤 AI 후보 생성·내용 검토를 다시 진행해주세요.';
  if (!proposal.review) return '내용 검토 전의 후보입니다. AI 후보 생성·내용 검토를 다시 진행해주세요.';
  if (proposal.review.issues.length) return `본문에 수정·확인 사항 ${proposal.review.issues.length}개가 남아 있습니다. 위 제안을 반영하거나 직접 수정하고, 저장한 본문을 다시 검토해주세요.`;
  return '';
}
export function clearReferenceDraft(key: string) {
  try { localStorage.removeItem(key); } catch { /* Browser storage failure must not hide a successful server save. */ }
}
