import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { AnalyzePage } from './pages/AnalyzePage';
import { LandingPage } from './pages/LandingPage';
import { ResultsPage } from './pages/ResultsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: 'analyze', element: <AnalyzePage /> },
      { path: 'results/:sessionId', element: <ResultsPage /> },
    ],
  },
], {
  basename: import.meta.env.BASE_URL,
});
