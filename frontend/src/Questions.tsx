import { DailyQuestion } from './DailyQuestion';
import { QuestionList } from './QuestionList';
import './questions.css';

export function QuestionInbox() {
  return <main className="page questions-page"><div className="breadcrumb">등록하기 <span>/</span> 질문함</div>
    <header className="reference-page-heading"><div><h1>궁금한 것을 남겨두세요.</h1><p>질문은 한 줄이면 충분합니다. 나중에 자료를 연결하고 직접 확인해보세요.</p></div></header>
    <DailyQuestion />
    <QuestionList />
  </main>;
}
