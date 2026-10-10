import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from "react-router-dom";
import CodeMirror from "@uiw/react-codemirror";
import { CodeBlock, codeExtensions } from "./CodeBlock";
import { Markdown } from "./Markdown";
import { PredictionInput } from "./PredictionInput";
import {
  api,
  assistanceLabels,
  type Assistance,
  ApiError,
  errorMessage,
  filenames,
  languages,
  difficulties,
  type Exercise,
  type Execution,
  type ProblemSet,
} from "./api";
import { ErrorNotice, useResource } from "./App";

const statuses: Record<string, string> = {
  ok: "실행 완료",
  passed: "테스트 통과",
  failed: "출력이 일치하지 않습니다",
  runtime_error: "실행 오류",
  compile_error: "컴파일 오류",
  time_limit: "실행 시간 초과",
  memory_limit: "메모리 제한 초과",
  output_limit: "출력 제한 초과",
  compile_time_limit: "컴파일 시간 초과",
  compile_output_limit: "컴파일 출력 제한 초과",
};

export function Practice({ review = false }: { review?: boolean }) {
  const { id } = useParams();
  const { data, error, reload } = useResource<ProblemSet>(review ? `/reviews/${id}` : `/sets/${id}`);
  const [params, setParams] = useSearchParams();
  const index = Math.max(0, data?.exercises.findIndex(exercise => exercise.id === params.get('exercise')) ?? 0);
  if (error)
    return (
      <main className="page">
        <ErrorNotice error={error} />
        <button onClick={reload}>다시 불러오기</button>
      </main>
    );
  if (!data)
    return (
      <main className="page" role="status">
        연습을 불러오는 중…
      </main>
    );
  return (
    <PracticeEditor
      key={data.review_id ?? data.exercises[index].id}
      problemSet={data}
      exercise={data.exercises[index]}
      index={index}
      onMove={(next) => {
        setParams({ exercise: data.exercises[next].id });
        reload();
      }}
    />
  );
}

function PracticeEditor({
  problemSet,
  exercise,
  index,
  onMove,
}: {
  problemSet: ProblemSet;
  exercise: Exercise;
  index: number;
  onMove: (index: number) => void;
}) {
  const navigate = useNavigate();
  const reviewId = problemSet.review_id;
  const helpQuery = reviewId ? `?review_id=${encodeURIComponent(reviewId)}` : "";
  const [assistance, setAssistance] = useState<Assistance>(exercise.assistance ?? "none");
  const initial = {
    code: exercise.progress?.code ?? exercise.starter,
    answer: exercise.progress?.answer ?? "",
  };
  const [code, setCode] = useState(initial.code);
  const [answer, setAnswer] = useState(initial.answer);
  const [saved, setSaved] = useState(initial);
  const revision = useRef(exercise.progress?.revision ?? 0);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState<{
    data: Execution;
    code: string;
    answer: string;
    action: string;
    stdin: string;
    test_code: string;
  } | null>(null);
  const [passed, setPassed] = useState(exercise.passed);
  const [destination, setDestination] = useState<number | "finish" | null>(null);
  const finishing = destination !== null;
  const [solution, setSolution] = useState<{ code: string; answer: string } | null>(null);
  const [solutionOpen, setSolutionOpen] = useState(false);
  const [solutionLoading, setSolutionLoading] = useState(false);
  const [solutionError, setSolutionError] = useState("");
  const comparison = useRef<HTMLDivElement>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [reported, setReported] = useState(false);
  const [attachAttempt, setAttachAttempt] = useState(false);
  const [stdin, setStdin] = useState(exercise.public_tests[0]?.stdin ?? "");
  const codeTests = exercise.test_mode === "code";
  const [testCode, setTestCode] = useState(exercise.public_tests[0]?.code ?? "");
  const [panel, setPanel] = useState("code");
  const [resultTab, setResultTab] = useState(codeTests ? "stdin" : "result");
  const actionLabels: Record<string, string> = {
    run: exercise.kind === "READ" ? "출력 확인" : codeTests ? "내 테스트 실행" : "직접 실행",
    test: "공개 테스트 검사",
    submit: "제출 · 채점",
  };
  const submission = useRef({ key: "", id: "" });
  const mounted = useRef(true);
  const dirty = code !== saved.code || answer !== saved.answer;
  const dirtyRef = useRef(dirty);
  dirtyRef.current = dirty;
  const blocker = useBlocker(dirty || !!busy || saving);
  const completedCount = problemSet.exercises.filter((item, i) => i === index ? passed : item.passed).length;

  useEffect(() => {
    if (solutionOpen && exercise.kind !== "READ") comparison.current?.scrollIntoView({ block: "nearest" });
  }, [solutionOpen, exercise.kind]);

  useEffect(() => {
    // Navigate only after the saved state has rendered and released useBlocker.
    if (destination === null || saving || dirty || busy) return;
    setDestination(null);
    if (destination === "finish") navigate(reviewId ? "/reviews" : `/learn/${problemSet.context_id}`);
    else onMove(destination);
  }, [destination, saving, dirty, busy, navigate, onMove, problemSet.context_id, reviewId]);
  const extensions = useMemo(
    () => codeExtensions(problemSet.language),
    [problemSet.language],
  );

  useEffect(() => {
    mounted.current = true;
    const leaving = (event: BeforeUnloadEvent) => {
      if (dirtyRef.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", leaving);
    return () => {
      mounted.current = false;
      window.removeEventListener("beforeunload", leaving);
    };
  }, []);

  async function save() {
    if (saving || conflict) return false;
    if (!dirty) return true;
    setSaving(true);
    setError("");
    const snapshot = { code, answer };
    try {
      const value = await api<{ revision: number }>(
        reviewId ? `/reviews/${reviewId}/progress` : `/exercises/${exercise.id}/progress`,
        "PUT",
        { ...snapshot, revision: revision.current },
      );
      if (mounted.current) {
        revision.current = value.revision;
        setSaved(snapshot);
      }
      return true;
    } catch (error) {
      if (mounted.current) {
        setError(errorMessage(error));
        if (error instanceof ApiError && error.status === 409)
          setConflict(true);
      }
      return false;
    } finally {
      if (mounted.current) setSaving(false);
    }
  }

  async function resolveConflict(keepLocal: boolean) {
    setSaving(true);
    try {
      const latest = await api<ProblemSet>(reviewId ? `/reviews/${reviewId}` : `/sets/${problemSet.id}`);
      const progress = latest.exercises.find(
        (item) => item.id === exercise.id,
      )?.progress;
      revision.current = progress?.revision ?? 0;
      const snapshot = {
        code: progress?.code ?? exercise.starter,
        answer: progress?.answer ?? "",
      };
      setSaved(snapshot);
      if (!keepLocal) {
        setCode(snapshot.code);
        setAnswer(snapshot.answer);
      }
      setConflict(false);
      setError("");
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function move(next: number) {
    setDestination(next);
    if (!await save()) setDestination(null);
  }

  async function finish() {
    setDestination("finish");
    if (!await save()) setDestination(null);
  }

  async function showSolution() {
    if (solutionOpen) { setSolutionOpen(false); return; }
    setSolutionOpen(true);
    if (exercise.kind !== "READ") setPanel("code");
    if (solution) return;
    setSolutionLoading(true);
    setSolutionError("");
    try {
      const value = await api<{ code: string; answer: string }>(`/exercises/${exercise.id}/solution${helpQuery}`);
      if (mounted.current) { setSolution(value); setAssistance("solution"); }
    } catch (error) {
      if (mounted.current) setSolutionError(errorMessage(error));
    } finally {
      if (mounted.current) setSolutionLoading(false);
    }
  }

  async function execute(action: "run" | "test" | "submit") {
    setBusy(action);
    setError("");
    const snapshot = { code, answer, stdin: codeTests ? "" : stdin, test_code: codeTests ? testCode : "" };
    const key = JSON.stringify({ action, ...snapshot });
    if (submission.current.key !== key)
      submission.current = { key, id: crypto.randomUUID() };
    try {
      const data = await api<Execution>(
        `/exercises/${exercise.id}/execute`,
        "POST",
        {
          ...snapshot,
          action,
          ...(reviewId ? { review_id: reviewId } : {}),
          version: problemSet.version,
          request_id: submission.current.id,
        },
      );
      if (mounted.current) {
        setResult({ data, ...snapshot, action });
        if (data.assistance) setAssistance(data.assistance);
        else if (exercise.kind === "READ" && action !== "submit" && data.status === "ok") setAssistance("solution");
        setResultTab("result");
        setPanel("result");
        if (action === "submit" && data.status === "passed") setPassed(true);
        submission.current = { key: "", id: "" };
      }
    } catch (error) {
      if (mounted.current) setError(errorMessage(error));
    } finally {
      if (mounted.current) setBusy("");
    }
  }

  async function nextHint() {
    setBusy("hint");
    setError("");
    try {
      const value = await api<{ hint: string }>(
        `/exercises/${exercise.id}/hints/${hints.length + 1}${helpQuery}`,
      );
      if (mounted.current) { setHints((values) => [...values, value.hint]); setAssistance(old => old === "solution" ? old : "hint"); }
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      if (mounted.current) setBusy("");
    }
  }

  async function sendReport() {
    setBusy("report");
    setError("");
    try {
      await api(`/exercises/${exercise.id}/reports`, "POST", {
        message,
        attempt_id: attachAttempt ? (result?.data.attempt_id ?? null) : null,
      });
      if (mounted.current) {
        setMessage("");
        setReported(true);
      }
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      if (mounted.current) setBusy("");
    }
  }

  return (
    <main className={`practice-page mobile-${panel}`}>
      <div className="practice-heading">
        <div>
          <Link to={`/learn/${problemSet.context_id}${problemSet.unit_id ? `/units/${problemSet.unit_id}` : ""}`} className="text-link">
            {problemSet.unit_id ? "← 개념 학습" : "← 학습 자료"}
          </Link>
          <h1>{reviewId ? "복습 · " : ""}{problemSet.title}</h1>
          <p className="muted">{assistanceLabels[assistance]} · {reviewId ? "이전 풀이와 별도로 저장됩니다." : "도움 사용은 제출 기록에 함께 남습니다."}</p>
        </div>
        <span className="language-tag">{languages[problemSet.language]} · {difficulties[problemSet.difficulty ?? 'beginner']}</span>
      </div>
      <nav className="stage-tabs" aria-label="학습 단계">
        {problemSet.exercises.map((item, i) => (
          <button
            key={item.id}
            disabled={!!busy || saving || finishing}
            aria-current={i === index ? "step" : undefined}
            className={i === index ? "active" : ""}
            onClick={() => void move(i)}
          >
            <span>
              {item.passed || (i === index && passed) ? "✓" : `0${i + 1}`}
            </span>
            {item.kind}
          </button>
        ))}
      </nav>
      <div className="mobile-panel-tabs" aria-label="풀이 영역">
        {[
          ["problem", "문제"],
          ["code", "코드"],
          ["result", exercise.kind === "READ" ? "결과" : "테스트 · 결과"],
        ].map(([key, text]) => (
          <button
            key={key}
            onClick={() => setPanel(key)}
            aria-pressed={panel === key}
          >
            {text}
          </button>
        ))}
      </div>
      <div className="practice-notices">
        <ErrorNotice error={error} />
        {conflict && (
          <div className="notice">
            <p>
              다른 탭의 저장 내용과 충돌했습니다. 현재 코드는 유지되어 있습니다.
            </p>
            <button
              disabled={saving}
              onClick={() => void resolveConflict(false)}
            >
              서버 내용 불러오기
            </button>
            <button
              disabled={saving}
              onClick={() => void resolveConflict(true)}
            >
              내 코드 유지 · 다음 저장에 덮어쓰기
            </button>
          </div>
        )}
        {problemSet.withdrawn && (
          <p className="notice">
            제공이 중단된 문제입니다. 작성 내용과 이전 기록은 보존됩니다.
          </p>
        )}
      </div>
      <div className="practice-grid">
        <section className="coding-column" aria-label="코드 작성">
          <div ref={comparison} className={`editor-comparison${solutionOpen && exercise.kind !== "READ" ? " is-open" : ""}`}>
            <div className="editor-panel">
              <div className="editor-header">
                <span>
                  <b className="file-icon">
                    {problemSet.language === "javascript" ? "JS" : "‹/›"}
                  </b>
                  {filenames[problemSet.language]}
                </span>
                <span className="save-status" role="status">
                  {saving ? "저장 중…" : dirty ? "저장하지 않은 변경" : "저장됨"}
                </span>
                <button
                  className="text-button"
                  onClick={() => void save()}
                  disabled={saving || !dirty || conflict}
                >
                  저장
                </button>
              </div>
              <CodeMirror
                onCreateEditor={(view) => view.contentDOM.setAttribute("aria-label", "코드 편집기")}
                value={code}
                theme="dark"
                height="420px"
                extensions={extensions}
                editable={exercise.kind !== "READ" && !finishing}
                onChange={setCode}
                aria-label="코드 편집기"
                basicSetup={{
                  lineNumbers: true,
                  foldGutter: false,
                  highlightActiveLine: true,
                }}
              />
              {exercise.kind === "READ" && (
                <PredictionInput answer={answer} onChange={setAnswer} disabled={finishing} />
              )}
              <div className="editor-footer">
                <span>
                  UTF-8 <span className="footer-separator">/</span>{" "}
                  {code.split("\n").length} lines
                </span>
                <span>
                  {exercise.kind === "READ"
                    ? "읽기 전용 코드"
                    : codeTests ? "풀이 코드 · 아래 테스트 코드와 함께 실행" : "단일 파일 · 표준 라이브러리"}
                </span>
              </div>
            </div>
            {solutionOpen && exercise.kind !== "READ" && (
              <section id="exercise-solution" className="solution-panel" aria-label="예시 정답 코드">
                <div className="editor-header">
                  <span>예시 정답 · 읽기 전용</span>
                  <button className="text-button" onClick={() => setSolutionOpen(false)}>정답 닫기</button>
                </div>
                {solutionLoading && <p role="status">정답 불러오는 중…</p>}
                <ErrorNotice error={solutionError} />
                {solution && <CodeMirror
                  onCreateEditor={(view) => view.contentDOM.setAttribute("aria-label", "예시 정답 편집기")}
                  value={solution.code}
                  theme="dark"
                  height="420px"
                  extensions={extensions}
                  editable={false}
                  readOnly
                  basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: false }}
                />}
                <p className="editor-footer">내 코드와 비교해보세요. 정답 확인만으로 완료 처리되지는 않습니다.</p>
              </section>
            )}
          </div>
          <div className="run-toolbar">
            <button
              onClick={() => void execute("run")}
              disabled={
                !!busy || finishing ||
                problemSet.withdrawn ||
                (exercise.kind === "READ" && !answer.trim())
              }
            >
              {busy === "run" ? "실행 중…" : `▷ ${actionLabels.run}`}
            </button>
            {exercise.kind !== "READ" && (
              <button
                onClick={() => void execute("test")}
                disabled={!!busy || finishing || problemSet.withdrawn}
              >
                {busy === "test" ? "검사 중…" : `✓ ${actionLabels.test}`}
              </button>
            )}
            <button
              className="primary"
              onClick={() => void execute("submit")}
              disabled={
                !!busy || finishing || (!!reviewId && passed) ||
                problemSet.withdrawn ||
                (exercise.kind === "READ" && !answer.trim())
              }
            >
              {busy === "submit" ? "채점 중…" : `${actionLabels.submit} →`}
            </button>
          </div>
          <p className="execution-help">
            {exercise.kind === "READ"
              ? "출력 확인은 정답 확인으로 기록됩니다. 제출·채점은 작성한 예상 출력을 채점하고 기록을 저장합니다."
              : "공개 테스트 검사는 문제의 예제를 확인합니다. 제출·채점은 비공개 테스트까지 검사하고 학습 기록을 저장합니다."}
          </p>
          <section className="result-panel" aria-label="실행 결과">
            <div className="result-tabs">
              <button
                className={resultTab === "result" ? "active" : ""}
                aria-pressed={resultTab === "result"}
                onClick={() => setResultTab("result")}
              >
                실행 결과
              </button>
              {exercise.kind !== "READ" && <button
                className={resultTab === "stdin" ? "active" : ""}
                aria-pressed={resultTab === "stdin"}
                onClick={() => setResultTab("stdin")}
              >
                {codeTests ? "내 테스트 코드" : "직접 실행 입력"}
              </button>}
              {(resultTab === "result" || !!busy) && <span className="muted">
                {busy && actionLabels[busy] ? `${actionLabels[busy]} 중…` : result ? actionLabels[result.action] : "실행 대기"}
              </span>}
            </div>
            {resultTab === "stdin" && codeTests ? (
              <div className="stdin-label">
                <div className="test-code-heading">
                  <strong>풀이 코드 + 아래 테스트 코드 → 실행 결과</strong>
                  <button onClick={() => void execute("run")} disabled={!!busy || finishing || problemSet.withdrawn}>
                    {busy === "run" ? "실행 중…" : "▷ 이 테스트 코드 실행"}
                  </button>
                </div>
                <p>위에서 작성한 함수를 아래에서 호출해보세요. 실행하면 출력이 ‘실행 결과’에 표시됩니다.</p>
                <CodeMirror
                  value={testCode}
                  onChange={setTestCode}
                  onCreateEditor={(view) => view.contentDOM.setAttribute("aria-label", "실행할 테스트 코드")}
                  theme="dark"
                  height="220px"
                  extensions={extensions}
                  basicSetup={{ lineNumbers: true, foldGutter: false }}
                />
                <p>직접 실행용 임시 코드입니다. 저장되지 않으며, 공개 테스트 검사와 제출·채점에는 사용되지 않습니다.</p>
              </div>
            ) : resultTab === "stdin" ? (
              <label className="stdin-label">
                표준 입력
                <textarea
                  value={stdin}
                  maxLength={2000}
                  onChange={(event) => setStdin(event.target.value)}
                />
              </label>
            ) : (
              <div className="result-content" role="status">
                {!result ? (
                  <p className="console-placeholder">
                    아직 실행한 코드가 없습니다.
                    <br />
                    <span>
                      {exercise.kind === "READ" ? "예상 출력을 작성한 뒤 제출·채점으로 확인하세요." : codeTests ? "내 테스트 코드에서 함수 호출을 작성하고 ‘이 테스트 코드 실행’을 누르세요." : "직접 실행 입력을 작성해 실행하거나, 공개 테스트 검사로 예제를 확인하세요."}
                    </span>
                  </p>
                ) : (
                  <>
                    <p
                      className={
                        ["passed", "ok"].includes(result.data.status)
                          ? "success-text"
                          : "error-text"
                      }
                    >
                      {statuses[result.data.status] ?? result.data.status}
                    </p>
                    {(code !== result.code || answer !== result.answer || (result.action === "run" && (codeTests ? testCode !== result.test_code : stdin !== result.stdin))) && (
                      <p className="notice">
                        이 결과는 변경 전 코드·답안·테스트 입력의 실행 결과입니다.
                      </p>
                    )}
                    {result.data.stdout && <pre>{result.data.stdout}</pre>}
                    {result.data.stderr && (
                      <pre className="error-text">{result.data.stderr}</pre>
                    )}
                    {codeTests && result.data.stderr.includes("SyntaxError: Identifier") && result.data.stderr.includes("has already been declared") && (
                      <p className="notice">풀이 코드와 테스트 코드에 같은 변수가 선언되어 있습니다. 문제에 필요한 구현은 유지하고, 예시 변수와 함수 호출은 테스트 코드 칸에만 두세요. 이전 단계의 변수가 남아 있는 것은 아닙니다.</p>
                    )}
                    {result.data.tests.map((test) => (
                      <details className="test-result" key={test.id}>
                        <summary>
                          <span
                            className={
                              test.passed ? "success-text" : "error-text"
                            }
                          >
                            {test.passed ? "✓" : "×"}
                          </span>
                          {test.id}
                          <span>{test.passed ? "통과" : "미통과"}</span>
                        </summary>
                        {test.stdin !== undefined ? (
                          <div>
                            <b>{test.code ? "테스트 코드" : "입력"}</b>
                            {test.code ? <CodeBlock code={test.code} language={problemSet.language} /> : <pre>{test.stdin || "(없음)"}</pre>}
                            <b>기대 출력</b>
                            <pre>{test.expected}</pre>
                            <b>실제 출력</b>
                            <pre>{test.actual || "(출력 없음)"}</pre>
                          </div>
                        ) : (
                          <p>비공개 평가 데이터는 표시하지 않습니다.</p>
                        )}
                      </details>
                    ))}
                    {result.action === "submit" && (
                      <small className="muted">
                        제출 기록이 저장되었습니다. {assistanceLabels[result.data.assistance ?? "unknown"]}. 자동 평가는 입력·출력 동작을
                        확인합니다.
                      </small>
                    )}
                  </>
                )}
              </div>
            )}
          </section>
        </section>
        <aside className="problem-panel">
          <div className="problem-top">
            <span className="eyebrow">{reviewId ? "REVIEW" : `EXERCISE 0${index + 1} / 04`}</span>
            <span className={passed ? "completion-badge" : "muted"}>
              {passed ? "✓ 완료" : `${exercise.attempt_count}회 제출`}
            </span>
          </div>
          <h2>{exercise.title}</h2>
          <Markdown language={problemSet.language}>{exercise.description}</Markdown>
          <h3>요구사항</h3>
          <ul className="requirements">
            {exercise.requirements.map((requirement) => (
              <li key={requirement.id}>
                <span>□</span>
                {requirement.text}
              </li>
            ))}
          </ul>
          {exercise.kind !== "READ" && (
            <>
              <h3>공개 테스트</h3>
              <p className="muted">‘공개 테스트 검사’는 아래 {exercise.public_tests.length}개 예제의 실제 출력과 예상 출력을 비교합니다.</p>
              {exercise.public_tests.map((test) => (
                <div className="example" key={test.id}>
                  <small>{codeTests ? "테스트 코드" : "INPUT"}</small>
                  {test.code ? <CodeBlock code={test.code} language={problemSet.language} /> : <pre>{test.stdin}</pre>}
                  <small>{codeTests ? "예상 출력" : "OUTPUT"}</small>
                  <pre>{test.expected}</pre>
                  {codeTests && <button className="text-button" onClick={() => {
                    setTestCode(test.code ?? "");
                    setResultTab("stdin");
                    setPanel("result");
                  }}>내 테스트 코드로 복사</button>}
                </div>
              ))}
            </>
          )}
          <div className="hint-section">
            <div className="section-heading">
              <h3>생각의 실마리</h3>
              <span className="muted">
                {hints.length} / {exercise.hints_count}
              </span>
            </div>
            {hints.map((hint, i) => (
              <p className="hint" key={i}>
                <b>힌트 {i + 1}</b>
                {hint}
              </p>
            ))}
            <button
              onClick={() => void nextHint()}
              disabled={
                !!busy ||
                hints.length >= exercise.hints_count ||
                problemSet.withdrawn
              }
            >
              ✧ {hints.length ? "다음 힌트 보기" : "힌트 열기"}
            </button>
          </div>
          <section className="solution-section">
            <button onClick={() => void showSolution()} disabled={solutionLoading}
              aria-expanded={solutionOpen} aria-controls="exercise-solution">
              {solutionLoading ? "정답 불러오는 중…" : solutionOpen ? "정답 닫기" : "정답 보기"}
            </button>
            {solutionOpen && exercise.kind === "READ" && <div id="exercise-solution">
              <ErrorNotice error={solutionError} />
              {solution && <>
                <h3>정답 출력</h3>
                <pre><code>{solution.answer}</code></pre>
                <p className="muted">내 풀이와 비교해보세요. 정답을 보는 것만으로 완료 처리되지는 않습니다.</p>
              </>}
            </div>}
          </section>
          <details className="report-form">
            <summary>문제 오류 제보</summary>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void sendReport();
              }}
            >
              <label>
                어떤 문제가 있나요?
                <textarea
                  value={message}
                  onChange={(event) => {
                    setMessage(event.target.value);
                    setReported(false);
                  }}
                  required
                  minLength={5}
                  maxLength={2000}
                />
              </label>
              {result?.data.attempt_id && (
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={attachAttempt}
                    onChange={(event) => setAttachAttempt(event.target.checked)}
                  />
                  현재 제출 기록 첨부
                </label>
              )}
              <small className="muted">
                작성 중인 코드는 자동 첨부하지 않습니다.
              </small>
              <button disabled={!!busy}>제보 보내기</button>
              {reported && (
                <p className="success-text" role="status">
                  제보가 접수되었습니다.
                </p>
              )}
            </form>
          </details>
          <div className="exercise-navigation">
            <button
              disabled={index === 0 || !!busy || saving || finishing}
              onClick={() => void move(index - 1)}
            >
              ← 이전
            </button>
            <button
              disabled={index === problemSet.exercises.length - 1 || !!busy || saving || finishing}
              onClick={() => void move(index + 1)}
            >
              다음 →
            </button>
          </div>
        </aside>
      </div>
      {(reviewId || exercise.kind === 'BUILD') && passed && <section className="practice-completion" aria-labelledby="completion-title">
        <div>
          <span className="eyebrow">{reviewId ? "REVIEW COMPLETE" : "BUILD COMPLETE"}</span>
          <h2 id="completion-title">{reviewId ? '복습을 완료했습니다' : completedCount === problemSet.exercises.length ? '이번 세트를 완료했습니다' : 'BUILD를 통과했습니다'}</h2>
          <p>{completedCount} / {problemSet.exercises.length} 단계 완료 · 제출한 풀이는 나의 기록에 저장되어 있습니다.</p>
        </div>
        <button className="primary" disabled={!!busy || saving || finishing || conflict} onClick={() => void finish()}>
          {finishing ? '저장하고 마무리하는 중…' : '학습 마무리 →'}
        </button>
      </section>}
      {blocker.state === "blocked" && (
        <div className="auth-backdrop">
          <section
            className="confirm-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="leave-title"
          >
            <h2 id="leave-title">연습 화면을 나갈까요?</h2>
            <p>
              {busy || saving
                ? "요청을 처리 중입니다. 제출은 화면을 떠나도 계속될 수 있습니다."
                : "저장하지 않은 내용이 있습니다."}
            </p>
            <button onClick={() => blocker.reset()}>계속 작성</button>
            <button
              disabled={!!busy || saving}
              onClick={() =>
                void save().then((ok) => {
                  if (ok) blocker.proceed();
                })
              }
            >
              저장 후 이동
            </button>
            <button className="text-button" onClick={() => blocker.proceed()}>
              저장하지 않고 이동
            </button>
          </section>
        </div>
      )}
    </main>
  );
}
