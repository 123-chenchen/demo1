import React from 'react';
import { Outlet } from 'react-router-dom';

import { useAppContext } from '../app/AppContext.jsx';
import { AppHeader } from '../components/AppHeader.jsx';

export function DashboardLayout() {
  const { header } = useAppContext();

  return (
    <div className="min-h-screen bg-zinc-100 text-zinc-950">
      <AppHeader {...header} />
      <Outlet />
    </div>
  );
}
