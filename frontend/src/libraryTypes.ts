export type RawKind = 'text' | 'url';
export type ResourceVersion = { revision: number; name: string; content: string | null; created_at?: string };
export type Resource = ResourceVersion & {
  id: string; note_id: string | null; kind: RawKind | 'note'; url: string | null;
  state: 'ready' | 'fetching' | 'failed'; error: string; updated_at: string; archived: number;
  versions: { revision: number; created_at: string }[];
};
export type ResourceList = { items: (Omit<Resource, 'content' | 'versions'> & { excerpt: string | null })[]; total: number; page: number; pages: number };
export type ResourceDraft = { request_id: string; kind: RawKind; name: string; url: string; content: string; revision: number; resource_id?: string };
export const resourceKinds = { text: '텍스트 · Markdown', url: '웹 레퍼런스', note: '직접 작성한 노트' };
export function libraryPage(value: string | null) {
  const page = Number(value);
  return Number.isSafeInteger(page) && page > 0 ? page : 1;
}
export function restoreResourceDraft(value: string | null, resourceId?: string): ResourceDraft | null {
  try {
    const draft = JSON.parse(value ?? 'null');
    if (!draft || draft.resource_id !== resourceId || !['text', 'url'].includes(draft.kind)
      || typeof draft.request_id !== 'string' || draft.request_id.length < 8 || draft.request_id.length > 80
      || !Number.isSafeInteger(draft.revision) || draft.revision < 0
      || !['name', 'url', 'content'].every(k => typeof draft[k] === 'string')
      || draft.name.length > 160 || draft.url.length > 2000 || draft.content.length > 60000) return null;
    return draft;
  } catch { return null; }
}

export async function readResourceFile(file: File): Promise<string> {
  if (!/\.(md|txt)$/i.test(file.name) || file.size > 240000) throw new Error('UTF-8 .md 또는 .txt 파일을 사용해주세요. 본문은 최대 60,000자입니다.');
  const text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer());
  if (text.length > 60000 || !text.trim()) throw new Error('본문은 1~60,000자로 입력해주세요.');
  return text;
}
