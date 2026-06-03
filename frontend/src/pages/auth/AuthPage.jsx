import React, { useEffect } from 'react';

import { useAppContext } from '../../app/AppContext.jsx';
import { AuthScreen } from '../../components/AuthScreen.jsx';

export function AuthPage({ mode }) {
  const { auth } = useAppContext();
  const { mode: currentMode, onModeChange } = auth;

  useEffect(() => {
    if (currentMode !== mode) {
      onModeChange(mode);
    }
  }, [currentMode, mode, onModeChange]);

  return <AuthScreen {...auth} mode={mode} />;
}
