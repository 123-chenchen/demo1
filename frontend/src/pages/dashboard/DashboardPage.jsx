import React from 'react';

import { useAppContext } from '../../app/AppContext.jsx';
import { ChatPanel } from '../../components/ChatPanel.jsx';
import { DocumentsPanel } from '../../components/DocumentsPanel.jsx';
import { NotebookPanel } from '../../components/NotebookPanel.jsx';
import { StatusSidebar } from '../../components/StatusSidebar.jsx';

export function DashboardPage() {
  const { isAuthDisabled, notebooks, documents, chat, status } = useAppContext();

  return (
    <main className="mx-auto grid max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[320px_minmax(0,1fr)_320px] lg:px-6">
      <aside className="space-y-4">
        {!isAuthDisabled && <NotebookPanel {...notebooks} />}
        <DocumentsPanel {...documents} />
      </aside>

      <ChatPanel {...chat} />

      <StatusSidebar {...status} />
    </main>
  );
}
