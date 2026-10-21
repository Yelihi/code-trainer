export type ReferenceMetadata = { kind: 'book' | 'lecture' | 'article' | 'experience' | 'other'; title: string; author: string; url: string; locator: string };
export const referenceKinds = { book: '책', lecture: '강의', article: '글 · 아티클', experience: '직접 경험', other: '기타' };
export const relations = { CLAIM: '주장', PREREQUISITE_OF: '선행 개념 → 후속 개념', BROADER_THAN: '상위 개념 → 하위 개념', USED_IN: '개념 → 활용 대상', RELATED_TO: '연관 개념 ↔ 개념' };
export const bases = { source: '출처에서 정리한 내용', interpretation: '나의 해석', question: '아직 풀리지 않은 질문' };
export type Concept = { id: string; pref_label: string; definition: string; scope: string; aliases: string[]; status: string };
export type Candidate = { key: string; existing_id: string; pref_label: string; definition: string; scope: string; aliases: string[]; quote: string; basis: keyof typeof bases };
export type Assertion = { subject: string; kind: keyof typeof relations; object: string; text: string; scope: string; quote: string; basis: keyof typeof bases; disposition: 'supports' | 'refutes' };
export type ProposalData = { concepts: Candidate[]; assertions: Assertion[] };
export type NoteContentReview = { summary: string; issues: { kind: 'correction_needed' | 'needs_verification'; quote: string; explanation: string; suggestion: string }[] };
export type Proposal = { id: string; revision: number; state: string; data: ProposalData | null; review: NoteContentReview | null; error: string };
export type ReferenceNote = { id: string; title: string; body: string; metadata: ReferenceMetadata; revision: number; archived: number; updated_at: string;
  registration: { id: string; version: number; state: string; created_at: string } | null;
  versions: { revision: number; created_at: string }[]; reviews: { id: string; state: string; created_at: string }[];
  proposal: { id: string; state: string; revision: number } | null };
export type ReviewSource = { id: string; note_id: string | null; title: string; version: number; body: string; metadata: ReferenceMetadata; relationship: string };
export type ReviewTurn = { role: 'user'; answer: string; request_id: string } | { role: 'assistant'; feedback: string; question: string; citations: string[] };
export type ReferenceReview = { id: string; note_id: string; revision: number; state: string; error: string; turns: ReviewTurn[]; sources: ReviewSource[] };
export const newReferenceId = () => crypto.randomUUID().replaceAll('-', '');
export function clearReferenceDraft(key: string) {
  try { localStorage.removeItem(key); } catch { /* Browser storage failure must not hide a successful server save. */ }
}
