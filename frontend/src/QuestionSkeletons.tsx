import { Skeleton } from './components/ui/skeleton';

export function QuestionTextSkeleton({ label = '질문을 불러오는 중' }: { label?: string }) {
  return <div className="question-text-skeleton" role="status"><span className="sr-only">{label}</span><div aria-hidden="true"><Skeleton /><Skeleton /><Skeleton /><Skeleton /></div></div>;
}

export function QuestionListSkeleton() {
  return <div role="status"><span className="sr-only">질문 목록을 불러오는 중</span><div aria-hidden="true">{[0, 1, 2].map(i => <div className="question-row question-row-skeleton" key={i}><span><Skeleton className="question-row-title-skeleton" /><Skeleton className="question-row-meta-skeleton" /></span><Skeleton className="question-row-action-skeleton" /></div>)}</div></div>;
}

export function QuestionGuideSkeleton() {
  return <div className="question-guide-skeleton" role="status"><span className="sr-only">가이드를 준비하고 있습니다</span><div aria-hidden="true"><Skeleton className="question-guide-title-skeleton" /><QuestionTextSkeleton /><QuestionTextSkeleton /></div></div>;
}

export function QuestionDetailSkeleton() {
  return <div className="question-detail-skeleton" aria-label="질문 상세를 불러오는 중" role="status"><span className="sr-only">질문 상세를 불러오는 중</span><div aria-hidden="true"><div className="question-detail-form"><Skeleton className="question-meta-skeleton" /><Skeleton className="question-input-skeleton" /><Skeleton className="question-meta-skeleton" /><Skeleton className="question-context-skeleton" /><Skeleton className="question-action-skeleton" /></div><section className="question-section question-follow-ups"><h2>이어지는 질문</h2><Skeleton className="question-relation-skeleton" /><div><Skeleton className="question-meta-skeleton" /><Skeleton className="question-context-skeleton" /><div className="question-feedback" /><Skeleton className="question-action-skeleton" /></div></section><section className="question-section"><h2>관련 자료</h2><QuestionTextSkeleton /></section><section className="question-section"><h2>AI 탐구 가이드</h2><QuestionGuideSkeleton /></section><section className="question-section"><h2>내 언어로 정리</h2><Skeleton className="question-action-skeleton" /></section></div></div>;
}
