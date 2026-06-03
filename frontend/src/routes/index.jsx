import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

import { AdminLayout } from '../layouts/AdminLayout.jsx';
import { AuthLayout } from '../layouts/AuthLayout.jsx';
import { DashboardLayout } from '../layouts/DashboardLayout.jsx';
import { NotFoundPage } from '../pages/system/NotFoundPage.jsx';
import { adminRoutes } from './adminRoutes.jsx';
import { authRoutes } from './authRoutes.jsx';
import { dashboardRoutes } from './dashboardRoutes.jsx';
import { AdminRoute, ProtectedRoute, PublicOnlyRoute } from './guards.jsx';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    element: <PublicOnlyRoute />,
    children: [
      {
        element: <AuthLayout />,
        children: authRoutes,
      },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          ...dashboardRoutes,
          {
            path: 'admin',
            element: <AdminRoute />,
            children: [
              {
                element: <AdminLayout />,
                children: adminRoutes,
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);
