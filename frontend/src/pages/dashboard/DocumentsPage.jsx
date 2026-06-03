import React from 'react';

import { useAppContext } from '../../app/AppContext.jsx';
import { DocumentsPanel } from '../../components/DocumentsPanel.jsx';
import { NotebookPanel } from '../../components/NotebookPanel.jsx';

export function DocumentsPage() {
  const { isAuthDisabled, notebooks, documents } = useAppContext();

  return (
    <main className="mx-auto grid max-w-5xl gap-4 px-4 py-4 lg:grid-cols-[320px_minmax(0,1fr)] lg:px-6">
      {!isAuthDisabled && <NotebookPanel {...notebooks} />}
      <div className="space-y-4">
        <DocumentsPanel {...documents} />
      </div>
    </main>
  );
}
