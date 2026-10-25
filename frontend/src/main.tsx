import { PlannedFeature, PracticeEntry } from './Navigation';
import { InterpretationCode } from './InterpretationCode';
import { Interpretations, InterpretationDetail } from './Interpretations';
import { WorksheetDetail } from './Worksheets';
import { PracticeRecordRoute } from './PracticeRecords';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
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
import './styles.css';

const router = createBrowserRouter([{ element: <App />, children: [
  { path: '/', element: <Home /> },
  { path: '/explore', element: <Interpretations /> },
  { path: '/interpretations/:id', element: <InterpretationDetail /> },
  { path: '/interpretations/:id/code/:sectionId', element: <InterpretationCode /> },
  { path: '/explore/practice', element: <PracticeEntry /> },
  { path: '/worksheets/:id', element: <WorksheetDetail /> },
  { path: '/worksheets/:id/practice', element: <PracticeRecordRoute /> },
  { path: '/knowledge/candidates', element: <PlannedFeature feature="candidates" /> },
  { path: '/apply', element: <PlannedFeature feature="inside" /> },
  { path: '/settings/ai', element: <AISettings /> },
  { path: '/inbox', element: <FeedInbox /> },
  { path: '/create', element: <Create /> },
  { path: '/learn/:id', element: <Context /> },
  { path: '/learn/:id/units/:unitId', element: <Lesson /> },
  { path: '/practice/:id', element: <Practice /> },
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
