import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { createRoot } from 'react-dom/client';

Object.assign(globalThis, { trainerRuntime: {
  modules: { react: React, 'react/jsx-runtime': jsxRuntime },
  mount: (App: React.ComponentType) => createRoot(document.getElementById('app')!).render(React.createElement(App)),
} });
