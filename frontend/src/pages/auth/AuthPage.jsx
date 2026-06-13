import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAppContext } from '../../app/AppContext.jsx';
import { AuthScreen } from '../../components/AuthScreen.jsx';

const authPaths = {
  login: '/login',
  register: '/register',
  reset: '/forgot-password',
  'reset-verify': '/reset-password',
};

const routeOwnedModes = {
  register: ['verify'],
  reset: ['reset-verify'],
};

export function AuthPage({ mode }) {
  const { auth } = useAppContext();
  const { mode: currentMode, onModeChange } = auth;
  const navigate = useNavigate();

  useEffect(() => {
    const isRouteOwnedMode = routeOwnedModes[mode]?.includes(currentMode);
    if (currentMode !== mode && !isRouteOwnedMode) {
      onModeChange(mode);
    }
  }, [currentMode, mode, onModeChange]);

  function handleModeChange(nextMode) {
    const nextPath = authPaths[nextMode];
    if (nextPath) {
      navigate(nextPath);
      return;
    }

    onModeChange(nextMode);
  }

  return <AuthScreen {...auth} mode={currentMode} onModeChange={handleModeChange} />;
}
