import React from 'react';
import { Navigate } from 'react-router-dom';

import { ChatPage } from '../pages/dashboard/ChatPage.jsx';
import { DashboardPage } from '../pages/dashboard/DashboardPage.jsx';
import { DocumentDetailPage } from '../pages/dashboard/DocumentDetailPage.jsx';
import { DocumentsPage } from '../pages/dashboard/DocumentsPage.jsx';
import { HistoryPage } from '../pages/dashboard/HistoryPage.jsx';
import { SettingsPage } from '../pages/dashboard/SettingsPage.jsx';

export const dashboardRoutes = [
  {
    path: 'dashboard',
    element: <DashboardPage />,
  },
  {
    path: 'chat',
    element: <ChatPage />,
  },
  {
    path: 'chat/:id',
    element: <ChatPage />,
  },
  {
    path: 'documents',
    element: <DocumentsPage />,
  },
  {
    path: 'documents/:id',
    element: <DocumentDetailPage />,
  },
  {
    path: 'history',
    element: <HistoryPage />,
  },
  {
    path: 'settings',
    element: <SettingsPage />,
  },
  {
    path: 'analytics',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: 'profile',
    element: <Navigate to="/settings" replace />,
  },
];
