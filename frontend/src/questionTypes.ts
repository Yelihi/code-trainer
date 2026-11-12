export type LinkItem = { resource_id: string; excerpt: string };
export type Question = { id: string; text: string; context: string; status: 'open' | 'done'; links: LinkItem[]; note_id: string | null; revision: number; updated_at: string };
export type Guide = { id: string; state: string; error: string; question_revision: number; result: { title: string; reading: string; checks: string[]; practice: string; expected_output: string; source_ids: string[] } | null };
export type Resource = { id: string; name: string; revision: number; state: string };
export type Daily = { day: string; recommendation: { id: string; source_kind: 'feed' | 'deep_inside'; source_title: string; source_url: string; text: string; saved_question_id: string | null; state: 'queued' | 'running' | 'ready' | 'failed'; error: string; evidence: string } | null; reason: string };

