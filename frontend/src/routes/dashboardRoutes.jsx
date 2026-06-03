import React from 'react';

import { AnalyticsPage } from '../pages/dashboard/AnalyticsPage.jsx';
import { ChatPage } from '../pages/dashboard/ChatPage.jsx';
import { DashboardPage } from '../pages/dashboard/DashboardPage.jsx';
import { DocumentDetailPage } from '../pages/dashboard/DocumentDetailPage.jsx';
import { DocumentsPage } from '../pages/dashboard/DocumentsPage.jsx';
import { HistoryPage } from '../pages/dashboard/HistoryPage.jsx';
import { ProfilePage } from '../pages/dashboard/ProfilePage.jsx';
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
    path: 'analytics',
    element: <AnalyticsPage />,
  },
  {
    path: 'settings',
    element: <SettingsPage />,
  },
  {
    path: 'profile',
    element: <ProfilePage />,
  },
];
