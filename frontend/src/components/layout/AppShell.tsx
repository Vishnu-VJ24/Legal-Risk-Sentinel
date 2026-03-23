import { Outlet, useLocation } from 'react-router-dom';
import { HeartFavorite } from '../ui/HeartFavorite';
import { Header } from './Header';

export const AppShell = () => {
  const location = useLocation();
  const isFullBleedPage = location.pathname === '/' || location.pathname === '/analyze';

  return (
    <div className="min-h-screen">
      <Header />
      <main
        className={
          isFullBleedPage
            ? 'flex min-h-[calc(100vh-72px)] w-full flex-col pb-10 pt-0'
            : 'mx-auto flex min-h-[calc(100vh-72px)] w-full max-w-7xl flex-col px-4 pb-10 pt-6 sm:px-6 lg:px-8'
        }
      >
        <Outlet />
      </main>
      <div className="pointer-events-none fixed bottom-5 right-4 z-40 sm:bottom-7 sm:right-6">
        <HeartFavorite className="pointer-events-auto" />
      </div>
    </div>
  );
};
