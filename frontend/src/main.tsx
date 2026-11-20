import { TechnicalReferences, TechnicalReferenceRoute } from './ReferenceWorkspace';
import { SpacedReviewRoute } from './SpacedReviews';
import { PracticeCatalog, PracticeEntry } from './Navigation';
import { InterpretationCode } from './InterpretationCode';
import { Interpretations, InterpretationDetail } from './Interpretations';
import { PracticeRecordRoute } from './PracticeRecords';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import { QuestionPolicySettings } from './QuestionPolicySettings';
import { Today } from './Today';
import { RecordSettings, LegacyTransition } from './RecordSettings';
import { App, Home, Create, Me } from './App';
import { Context, Lesson } from './Learning';
import { Practice } from './Practice';
import { Sources } from './Sources';
import { Reviews, Operations } from './Reviews';
import { FeedInbox } from './FeedInbox';
import { Foundations, FoundationLesson } from './Foundations';
import { Library, ResourceRegister, ResourceDetail } from './Library';
import { ReferenceNoteRoute } from './ReferenceNotes';
import { ReferenceReview } from './ReferenceReview';
import { GitHubSettings, GitHubShare } from './GitHubSharing';
import { AISettings } from './AISettings';
import { QuestionInbox } from './Questions';
import { QuestionDetail } from './QuestionDetail';
import './shadcn.css';
import './styles.css';
import './learning.css';
import './settings.css';
import './foundationLearning.css';
import './home.css';

const router = createBrowserRouter([{ element: <App />, children: [
  { path: '/', element: <Today /> },
  { path: '/technical-references', element: <TechnicalReferences /> },
  { path: '/technical-references/new', element: <TechnicalReferenceRoute /> },
  { path: '/technical-references/:id', element: <TechnicalReferenceRoute /> },
  { path: '/technical-references/:id/legacy', element: <TechnicalReferenceRoute /> },
  { path: '/courses', element: <Home /> },
  { path: '/settings/questions', element: <QuestionPolicySettings /> },
  { path: '/settings/records', element: <RecordSettings /> },
  { path: '/explore', element: <Interpretations /> },
  { path: '/interpretations/:id', element: <InterpretationDetail /> },
  { path: '/interpretations/:id/code/:sectionId', element: <InterpretationCode /> },
  { path: '/explore/practice', element: <PracticeEntry /> },
  { path: '/explore/practice/catalog', element: <PracticeCatalog /> },
  { path: '/worksheets/:id/practice', element: <PracticeRecordRoute /> },
  { path: '/problem-books/*', element: <Navigate to="/explore/practice" replace /> },
  { path: '/framework-practice', element: <Navigate to="/explore/practice" replace /> },
  { path: '/worksheets/:id', element: <Navigate to="/explore/practice" replace /> },
  { path: '/knowledge/*', element: <Navigate to="/technical-references" replace /> },
  { path: '/questions', element: <QuestionInbox /> },
  { path: '/questions/:id', element: <QuestionDetail /> },
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
  { path: '/settings/github', element: <GitHubSettings /> },
  { path: '/github/share', element: <GitHubShare /> },
  { path: '/library', element: <Library /> },
  { path: '/library/new/reference', element: <ResourceRegister /> },
  { path: '/library/:id', element: <ResourceDetail /> },
  { path: '/library/:id/edit', element: <ResourceRegister /> },
  { path: '/references', element: <Navigate to="/library" replace /> },
  { path: '/references/new', element: <ReferenceNoteRoute /> },
  { path: '/references/:id', element: <ReferenceNoteRoute /> },
  { path: '/reference-reviews/:id', element: <ReferenceReview /> },
  { path: '/admin/sources', element: <Sources /> },
  { path: '/admin/sources/:sourceId', element: <Sources /> },
  { path: '*', element: <main className="page"><h1>페이지를 찾을 수 없습니다.</h1><a href="/">학습 공간으로</a></main> },
] }]);

createRoot(document.getElementById('root')!).render(<StrictMode><RouterProvider router={router} /></StrictMode>);
