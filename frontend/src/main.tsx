import { TechnicalReferences, TechnicalReferenceRoute } from './TechnicalReferences';
import { SpacedReviewRoute } from './SpacedReviews';
import { KnowledgeCandidates, KnowledgeCandidateDetail } from './KnowledgeCandidates';
import { PracticeEntry } from './Navigation';
import { InterpretationCode } from './InterpretationCode';
import { FrameworkPractice } from './FrameworkPractice';
import { Interpretations, InterpretationDetail } from './Interpretations';
import { WorksheetDetail } from './Worksheets';
import { ProblemBookCatalog, ProblemBank, ProblemEditor, BookEditor, BookDetail, SolveProblem } from './ProblemBooks';
import { PracticeRecordRoute } from './PracticeRecords';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { Today } from './Today';
import { RecordSettings, LegacyTransition } from './RecordSettings';
import { App, Home, Create, Me } from './App';
import { Context, Lesson } from './Learning';
import { Practice } from './Practice';
import { Sources } from './Sources';
import { Reviews, Operations } from './Reviews';
import { FeedInbox } from './FeedInbox';
import { Foundations, FoundationLesson } from './Foundations';
import { LearningMap } from './LearningMap';
import { Library, ResourceRegister, ResourceDetail } from './Library';
import { ReferenceNotes, ReferenceNoteRoute } from './ReferenceNotes';
import { ReferenceReview } from './ReferenceReview';
import { GitHubSettings, GitHubShare } from './GitHubSharing';
import { AISettings } from './AISettings';
import { QuestionInbox } from './Questions';
import { QuestionDetail } from './QuestionDetail';
import './shadcn.css';
import './styles.css';
import './learning.css';

const router = createBrowserRouter([{ element: <App />, children: [
  { path: '/', element: <Today /> },
  { path: '/technical-references', element: <TechnicalReferences /> },
  { path: '/technical-references/new', element: <TechnicalReferenceRoute /> },
  { path: '/technical-references/:id', element: <TechnicalReferenceRoute /> },
  { path: '/courses', element: <Home /> },
  { path: '/settings/records', element: <RecordSettings /> },
  { path: '/explore', element: <Interpretations /> },
  { path: '/interpretations/:id', element: <InterpretationDetail /> },
  { path: '/interpretations/:id/code/:sectionId', element: <InterpretationCode /> },
  { path: '/framework-practice', element: <FrameworkPractice /> },
  { path: '/explore/practice', element: <PracticeEntry /> },
  { path: '/worksheets/:id', element: <WorksheetDetail /> },
  { path: '/worksheets/:id/practice', element: <PracticeRecordRoute /> },
  { path: '/problem-books', element: <ProblemBookCatalog /> },
  { path: '/questions', element: <QuestionInbox /> },
  { path: '/questions/:id', element: <QuestionDetail /> },
  { path: '/problem-books/new', element: <BookEditor /> },
  { path: '/problem-books/problems', element: <ProblemBank /> },
  { path: '/problem-books/problems/new', element: <ProblemEditor /> },
  { path: '/problem-books/problems/:id/edit', element: <ProblemEditor /> },
  { path: '/problem-books/problems/:id/solve', element: <SolveProblem /> },
  { path: '/problem-books/:id/edit', element: <BookEditor /> },
  { path: '/problem-books/:id', element: <BookDetail /> },
  { path: '/knowledge/candidates', element: <KnowledgeCandidates /> },
  { path: '/knowledge/candidates/:id', element: <KnowledgeCandidateDetail /> },
  { path: '/project-brain/*', element: <LegacyTransition /> },
  { path: '/apply/*', element: <LegacyTransition /> },
  { path: '/settings/ai', element: <AISettings /> },
  { path: '/inbox', element: <FeedInbox /> },
  { path: '/create', element: <Create /> },
  { path: '/learn/:id', element: <Context /> },
  { path: '/learn/:id/units/:unitId', element: <Lesson /> },
  { path: '/practice/:id', element: <Practice /> },
  { path: '/reviews/material/:id', element: <SpacedReviewRoute /> },
  { path: '/reviews', element: <Reviews /> },
  { path: '/reviews/:id', element: <Practice review /> },
  { path: '/admin/operations', element: <Operations /> },
  { path: '/foundations', element: <Foundations /> },
  { path: '/foundations/:id', element: <FoundationLesson key="concept" /> },
  { path: '/foundations/:id/practice', element: <FoundationLesson key="practice" practice /> },
  { path: '/me', element: <Me /> },
  { path: '/knowledge', element: <LearningMap /> },
  { path: '/settings/github', element: <GitHubSettings /> },
  { path: '/github/share', element: <GitHubShare /> },
  { path: '/library', element: <Library /> },
  { path: '/library/new/reference', element: <ResourceRegister /> },
  { path: '/library/:id', element: <ResourceDetail /> },
  { path: '/library/:id/edit', element: <ResourceRegister /> },
  { path: '/references', element: <ReferenceNotes /> },
  { path: '/references/new', element: <ReferenceNoteRoute /> },
  { path: '/references/:id', element: <ReferenceNoteRoute /> },
  { path: '/reference-reviews/:id', element: <ReferenceReview /> },
  { path: '/admin/sources', element: <Sources /> },
  { path: '/admin/sources/:sourceId', element: <Sources /> },
  { path: '*', element: <main className="page"><h1>페이지를 찾을 수 없습니다.</h1><a href="/">학습 공간으로</a></main> },
] }]);

createRoot(document.getElementById('root')!).render(<StrictMode><RouterProvider router={router} /></StrictMode>);
