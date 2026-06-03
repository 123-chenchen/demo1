import React from 'react';
import { RouterProvider } from 'react-router-dom';

import { AppProvider } from './app/AppContext.jsx';
import { router } from './routes/index.jsx';

function App() {
  return (
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>
  );
}

export default App;
