export type Language = 'javascript' | 'typescript' | 'python' | 'cpp' | 'rust';
export type Difficulty = 'beginner' | 'intermediate' | 'advanced';
export const difficulties: Record<Difficulty, string> = { beginner: '초급', intermediate: '중급', advanced: '고급' };
export const difficultyDescriptions: Record<Difficulty, string> = { beginner: '한 가지 개념부터, 충분한 예시와 함께 연습합니다.', intermediate: '관련 개념을 조합하고 경계 조건과 상태 변화를 다룹니다.', advanced: '자료 안의 개념을 응용해 여러 단계의 동작과 복잡한 조건을 다룹니다.' };
export const languages: Record<Language, string> = { javascript: 'JavaScript', typescript: 'TypeScript', python: 'Python', cpp: 'C++', rust: 'Rust' };
export const filenames: Record<Language, string> = { javascript: 'main.js', typescript: 'main.ts', python: 'main.py', cpp: 'main.cpp', rust: 'main.rs' };
export type Session = { user: { id: string; username: string; admin: number } | null; setup_required: boolean; auth_mode?: 'local' | 'access' };
export type Health = { sandbox: boolean; ai: boolean; languages: string[] };
export type SetSummary = { id: string; title: string; unit_id?: string | null; completed: number; total: number; withdrawn: boolean };
export type LearningUnit = { id: string; title: string; objective: string; concepts: string[]; prerequisites: string[]; rationale: string; lesson: { title: string; body: string; code: string; output: string; walkthrough: string }[]; pitfalls: string[]; checkpoints: { question: string; answer: string }[] };
export type LearningContext = { id: string; title: string; description: string; summary: string; concepts: string[]; language: Language; difficulty?: Difficulty; source_url?: string; created_at: string; completed: number; total: number; sets?: SetSummary[]; units?: LearningUnit[]; generation?: Generation | null; unit_generations?: Generation[] };
export type GenerationEvent = { time: string; level: string; message: string; phase?: string; kind?: string; code?: string; model?: string; candidate?: number; unit?: number; elapsed_seconds?: number; check?: string; status?: string; issues?: { path: string; label?: string; type: string; reason: string }[] };
export type Generation = { id: string; state: string; stage: string; context_id?: string; set_id?: string; unit_id?: string | null; error?: string; events?: GenerationEvent[] };
export type Exercise = { id: string; kind: 'READ' | 'FIX' | 'MODIFY' | 'BUILD'; test_mode: 'stdio' | 'code'; title: string; description: string; requirements: { id: string; text: string }[]; starter: string; public_tests: { id: string; code?: string; stdin: string; expected: string; requirements: string[] }[]; hints_count: number; progress: { code: string; answer: string; revision: number } | null; passed: boolean; attempt_count: number };
export type ProblemSet = { id: string; context_id: string; unit_id?: string | null; title: string; version: number; language: Language; difficulty?: Difficulty; withdrawn: boolean; exercises: Exercise[] };
export type Execution = { status: string; stdout: string; stderr: string; exit_code: number | null; tests: { id: string; passed: boolean; code?: string; stdin?: string; expected?: string; actual?: string }[]; attempt_id?: string };
export type LearnedUnit = { context_id: string; context_title: string; unit_id: string | null; title: string; set_id: string; withdrawn: boolean; completed: number; total: number; exercises: { id: string; kind: string; title: string; passed: boolean; attempted: boolean }[] };
export type History = { learning_map: { key: string; label: string; framework: boolean; concepts: { name: string; units: LearnedUnit[] }[] }[]; sets: { id: string; title: string; context_title: string; completed: number; total: number; updated_at: string }[]; attempts: { id: string; exercise_id: string; kind: string; title: string; status: string; created_at: string }[]; reports: { id: string; message: string; exercise_title: string; created_at: string; status: string }[] };

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

export async function api<T>(path: string, method = 'GET', data?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method, credentials: 'same-origin', signal,
    headers: data === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('session-expired', { detail: response.headers.get('X-Trainer-Auth') }));
    throw new ApiError(response.status, typeof body?.detail === 'string' ? body.detail : `요청을 처리하지 못했습니다 (${response.status}).`);
  }
  if (body === null) throw new ApiError(502, '서버 응답을 확인하지 못했습니다. 화면을 새로고침해주세요.');
  return body as T;
}

export function errorMessage(error: unknown) { return error instanceof Error ? error.message : '요청을 처리하지 못했습니다. 다시 시도해주세요.'; }
export function isPending(generation: Generation) { return !['ready', 'failed'].includes(generation.state); }
export function safeSourceUrl(value?: string): string | undefined {
  if (!value) return;
  try { const url = new URL(value); if (url.protocol === 'http:' || url.protocol === 'https:') return url.href; } catch { /* Invalid attribution is shown without a link. */ }
}
export function timestamp(value: string) { return new Date(value).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
