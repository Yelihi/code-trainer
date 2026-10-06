import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { App, Home, Create, Me } from './App';
import { Context, Lesson } from './Learning';
import { Practice } from './Practice';
import { Sources } from './Sources';
import { Reviews, Operations } from './Reviews';
import './styles.css';

const router = createBrowserRouter([{ element: <App />, children: [
  { path: '/', element: <Home /> },
  { path: '/create', element: <Create /> },
  { path: '/learn/:id', element: <Context /> },
  { path: '/learn/:id/units/:unitId', element: <Lesson /> },
  { path: '/practice/:id', element: <Practice /> },
  { path: '/reviews', element: <Reviews /> },
  { path: '/reviews/:id', element: <Practice review /> },
  { path: '/admin/operations', element: <Operations /> },
  { path: '/me', element: <Me /> },
  { path: '/admin/sources', element: <Sources /> },
  { path: '/admin/sources/:sourceId', element: <Sources /> },
  { path: '*', element: <main className="page"><h1>페이지를 찾을 수 없습니다.</h1><a href="/">학습 공간으로</a></main> },
] }]);

createRoot(document.getElementById('root')!).render(<StrictMode><RouterProvider router={router} /></StrictMode>);
