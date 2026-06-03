import React, { createContext, useContext } from 'react';

import { usePdfChatbotApp } from '../usePdfChatbotApp.js';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const app = usePdfChatbotApp();

  return <AppContext.Provider value={app}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
}
