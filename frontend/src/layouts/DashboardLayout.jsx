import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import { useAppContext } from '../app/AppContext.jsx';
import { AppHeader } from '../components/AppHeader.jsx';

export function DashboardLayout() {
  const { header } = useAppContext();
  const location = useLocation();
  const isNotebookRoute = location.pathname === '/dashboard' || location.pathname.startsWith('/chat');

  return (
    <div className={`flex flex-col bg-zinc-100 text-zinc-950 ${isNotebookRoute ? 'h-screen overflow-hidden' : 'min-h-screen overflow-visible'}`}>
      <AppHeader {...header} />
      <div className={`flex-1 ${isNotebookRoute ? 'min-h-0 overflow-hidden' : 'overflow-visible'}`}>
        <Outlet />
      </div>
    </div>
  );
}
