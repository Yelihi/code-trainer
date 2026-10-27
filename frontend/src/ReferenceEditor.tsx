import { useRef, useState } from 'react';
import { api, errorMessage } from './api';
import { Markdown } from './Markdown';
import { ErrorNotice } from './App';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';
import { Input } from './components/ui/input';

export function ReferenceEditor({ value, onChange, disabled = false, onUploading }: { value: string; onChange: (value: string) => void; disabled?: boolean; onUploading: (busy: boolean) => void }) {
  const input = useRef<HTMLTextAreaElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const currentValue = useRef(value);
  currentValue.current = value;
  const [mode, setMode] = useState<'write' | 'split' | 'preview'>('split');
  const [uploading, setUploading] = useState(false);
  const uploadLock = useRef(false);
  const [error, setError] = useState('');
  function insert(before: string, after = '', placeholder = '') {
    const element = input.current;
    const start = element?.selectionStart ?? currentValue.current.length;
    const end = element?.selectionEnd ?? start;
    const selected = currentValue.current.slice(start, end) || placeholder;
    onChange(currentValue.current.slice(0, start) + before + selected + after + currentValue.current.slice(end));
    requestAnimationFrame(() => { element?.focus(); element?.setSelectionRange(start + before.length, start + before.length + selected.length); });
  }
  async function upload(files: File[]) {
    if (disabled || uploadLock.current || !files.length) return;
    uploadLock.current = true; setUploading(true); onUploading(true); setError('');
    const markdown: string[] = [];
    try {
      for (const file of files.slice(0, 8)) {
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 4 * 1024 * 1024) throw new Error('PNG·JPEG·WebP 이미지를 4 MB 이하로 첨부해주세요.');
        const content = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result).split(',')[1]);
          reader.onerror = () => reject(new Error('파일을 읽지 못했습니다.'));
          reader.readAsDataURL(file);
        });
        const result = await api<{ url: string }>('/reference-images', 'POST', { name: file.name.slice(0, 200), content });
        markdown.push(`![${file.name.replace(/[[\]\\\r\n]/g, ' ').slice(0, 120) || '첨부 이미지'}](${result.url})`);
      }
      if (files.length > 8) setError('한 번에 8장까지 첨부했습니다. 나머지는 다시 첨부해주세요.');
    } catch (e) { setError(errorMessage(e)); }
    finally {
      if (markdown.length) insert('\n\n' + markdown.join('\n\n') + '\n\n');
      uploadLock.current = false; setUploading(false); onUploading(false);
      if (fileInput.current) fileInput.current.value = '';
    }
  }
  return <section className={`reference-editor mode-${mode}`} aria-label="노트 본문 에디터">
    <div className="reference-editor-toolbar">
      <div className="reference-formatting" role="group" aria-label="본문 서식">
        <Button type="button" disabled={disabled || mode === 'preview'} onClick={() => insert('## ', '', '소제목')} title="소제목">H2</Button>
        <Button type="button" disabled={disabled || mode === 'preview'} onClick={() => insert('**', '**', '강조할 내용')} aria-label="굵게"><strong>B</strong></Button>
        <Button type="button" disabled={disabled || mode === 'preview'} onClick={() => insert('*', '*', '기울일 내용')} aria-label="기울임"><em>I</em></Button>
        <Button type="button" disabled={disabled || mode === 'preview'} onClick={() => insert('\n- ', '', '목록')} aria-label="목록">≡</Button>
        <Button type="button" disabled={disabled || mode === 'preview'} onClick={() => insert('\n> ', '', '인용문')} aria-label="인용">“ ”</Button>
        <Button type="button" disabled={disabled || mode === 'preview'} onClick={() => insert('[', '](https://)', '링크 이름')} aria-label="링크">링크</Button>
        <Button type="button" disabled={disabled || mode === 'preview'} onClick={() => insert('\n```\n', '\n```\n', '코드 또는 예시')} aria-label="코드 블록">{'<>'}</Button>
        <Button type="button" disabled={disabled || uploading} onClick={() => fileInput.current?.click()}>사진 첨부</Button>
        <Input ref={fileInput} hidden type="file" aria-label="첨부할 이미지" accept="image/png,image/jpeg,image/webp" multiple onChange={e => void upload(Array.from(e.target.files ?? []))} />
      </div>
      <div className="reference-editor-modes" role="group" aria-label="에디터 보기">
        {([['write', '작성'], ['split', '함께 보기'], ['preview', '미리보기']] as const).map(([key, label]) => <Button type="button" key={key} aria-pressed={mode === key} onClick={() => setMode(key)}>{label}</Button>)}
      </div>
    </div>
    <ErrorNotice error={error} />
    {uploading && <p role="status" className="notice">이미지를 첨부하고 있습니다…</p>}
    <div className="reference-editor-body"
      onDragOver={e => { if (e.dataTransfer.types.includes('Files')) e.preventDefault(); }}
      onDrop={e => { if (e.dataTransfer.files.length) { e.preventDefault(); void upload(Array.from(e.dataTransfer.files)); } }}>
      {mode !== 'preview' && <Textarea ref={input} aria-label="노트 본문" value={value} disabled={disabled || uploading} maxLength={60000}
        placeholder={'오늘 이해한 내용을 자유롭게 적어보세요.\n\n## 핵심 내용\n\n## 내 생각과 예시\n\n## 남은 질문\n\n사진을 붙여넣거나 이곳에 끌어다 놓을 수 있습니다.'}
        onChange={e => onChange(e.target.value)}
        onPaste={e => { const files = Array.from(e.clipboardData.files).filter(f => f.type.startsWith('image/')); if (files.length) { e.preventDefault(); void upload(files); } }}
        onKeyDown={e => { if ((e.metaKey || e.ctrlKey) && e.key === 'b') { e.preventDefault(); insert('**', '**', '강조할 내용'); } }} />}
      {mode !== 'write' && <div className="reference-preview" aria-label="본문 미리보기">{value ? <Markdown language="" images>{value}</Markdown> : <div className="reference-preview-empty"><span>YOUR OWN WORDS</span><p>읽고, 생각하고, 기록하세요.</p><small>작성한 내용이 이곳에 미리 표시됩니다.</small></div>}</div>}
    </div>
    <footer><span>Markdown · 이미지 붙여넣기 / 드래그 첨부</span><span>{value.length.toLocaleString()} / 60,000자</span></footer>
  </section>;
}
