import { PageHeading } from './WorkspaceUI';
import { QuestionList } from './QuestionList';
import './questions.css';

export function QuestionInbox() {
  return <main className="page questions-page"><div className="breadcrumb">오늘의 학습 <span>/</span> 질문</div>
    <PageHeading title="내 질문" description="남겨둔 궁금증을 다시 읽고, 자료와 연결해보세요." />
    <QuestionList />
  </main>;
}
