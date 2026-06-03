import React from 'react';

import { AdminDashboardPage } from '../pages/admin/AdminDashboardPage.jsx';
import { AdminUserPage } from '../pages/admin/AdminUserPage.jsx';

export const adminRoutes = [
  {
    index: true,
    element: <AdminDashboardPage />,
  },
  {
    path: 'users/:userId',
    element: <AdminUserPage />,
  },
];
