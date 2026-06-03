import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAppContext } from '../app/AppContext.jsx';
import { AccessDeniedPage } from '../pages/system/AccessDeniedPage.jsx';

function isAdminUser(user) {
  return Boolean(user?.is_admin || user?.isAdmin || user?.role === 'admin' || user?.roles?.includes?.('admin'));
}

export function ProtectedRoute() {
  const { isAuthenticated } = useAppContext();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function PublicOnlyRoute() {
  const { isAuthenticated } = useAppContext();
  const location = useLocation();
  const nextPath = location.state?.from?.pathname || '/dashboard';

  if (isAuthenticated) {
    return <Navigate to={nextPath} replace />;
  }

  return <Outlet />;
}

export function AdminRoute() {
  const { header } = useAppContext();

  if (!isAdminUser(header.user)) {
    return <AccessDeniedPage />;
  }

  return <Outlet />;
}
