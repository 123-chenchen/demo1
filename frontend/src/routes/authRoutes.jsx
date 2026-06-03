import React from 'react';

import { AuthPage } from '../pages/auth/AuthPage.jsx';

export const authRoutes = [
  {
    path: 'login',
    element: <AuthPage mode="login" />,
  },
  {
    path: 'register',
    element: <AuthPage mode="register" />,
  },
  {
    path: 'forgot-password',
    element: <AuthPage mode="reset" />,
  },
  {
    path: 'reset-password',
    element: <AuthPage mode="reset-verify" />,
  },
];
