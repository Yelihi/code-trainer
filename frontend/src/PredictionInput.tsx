import { useId, useLayoutEffect, useRef } from "react";

export function replaceOutputLine(answer: string, index: number, value: string | null) {
  const lines = answer.split("\n");
  lines.splice(index, 1, ...(value === null ? [] : [value]));
  return lines.join("\n");
}

export function PredictionInput({ answer, onChange, disabled }: {
  answer: string;
  onChange: (answer: string) => void;
  disabled: boolean;
}) {
  const id = useId();
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const focus = useRef<{ index: number; caret: number } | null>(null);
  const lines = answer.split("\n");
  const remaining = Math.max(0, 4000 - answer.length);

  useLayoutEffect(() => {
    if (!focus.current) return;
    const { index, caret } = focus.current;
    inputs.current[index]?.focus();
    inputs.current[index]?.setSelectionRange(caret, caret);
    focus.current = null;
  }, [answer]);

  function addLine(index: number) {
    if (!remaining) return;
    focus.current = { index: index + 1, caret: 0 };
    onChange(replaceOutputLine(answer, index, `${lines[index]}\n`));
  }

  return (
    <div className="prediction" role="group" aria-labelledby={`${id}-title`}>
      <strong id={`${id}-title`}>예상 출력</strong>
      <p id={`${id}-help`} className="prediction-help">
        출력 순서대로 한 줄씩 입력하세요. 같은 줄의 값은 공백으로 구분하세요.
        Enter로 줄을 추가하거나 여러 줄을 붙여넣을 수 있어요.
      </p>
      <div className="prediction-lines">
        {lines.map((line, index) => (
          <div className="prediction-line" key={index}>
            <label htmlFor={`${id}-${index}`}>{index + 1}</label>
            <input
              id={`${id}-${index}`}
              ref={(input) => { inputs.current[index] = input; }}
              aria-label={`예상 출력 ${index + 1}번째 줄`}
              aria-describedby={`${id}-help`}
              value={line}
              disabled={disabled}
              maxLength={line.length + remaining}
              autoComplete="off"
              spellCheck={false}
              placeholder="출력될 값을 입력하세요"
              onChange={(event) => onChange(replaceOutputLine(answer, index, event.target.value))}
              onKeyDown={(event) => {
                if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
                event.preventDefault();
                addLine(index);
              }}
              onPaste={(event) => {
                event.preventDefault();
                const start = event.currentTarget.selectionStart ?? line.length;
                const end = event.currentTarget.selectionEnd ?? start;
                const text = event.clipboardData.getData("text").replace(/\r\n?/g, "\n")
                  .slice(0, remaining + end - start);
                const before = line.slice(0, start) + text;
                const nextAnswer = replaceOutputLine(answer, index, before + line.slice(end));
                if (nextAnswer === answer) return;
                const pastedLines = before.split("\n");
                focus.current = { index: index + pastedLines.length - 1, caret: pastedLines.at(-1)!.length };
                onChange(nextAnswer);
              }}
            />
            <button
              type="button"
              aria-label={`예상 출력 ${index + 1}번째 줄 삭제`}
              disabled={disabled || lines.length === 1}
              onClick={() => {
                focus.current = { index: Math.max(0, index - 1), caret: 0 };
                onChange(replaceOutputLine(answer, index, null));
              }}
            >삭제</button>
          </div>
        ))}
      </div>
      <div className="prediction-actions">
        <button type="button" disabled={disabled || !remaining} onClick={() => addLine(lines.length - 1)}>
          + 출력 줄 추가
        </button>
        <span>{answer.length.toLocaleString()} / 4,000자</span>
      </div>
    </div>
  );
}
