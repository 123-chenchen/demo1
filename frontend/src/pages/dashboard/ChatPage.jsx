import React from 'react';
import { useParams } from 'react-router-dom';

import { useAppContext } from '../../app/AppContext.jsx';
import { ChatPanel } from '../../components/ChatPanel.jsx';
import { StatusSidebar } from '../../components/StatusSidebar.jsx';

export function ChatPage() {
  const { id } = useParams();
  const { chat, status } = useAppContext();

  return (
    <main className="mx-auto grid max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[minmax(0,1fr)_320px] lg:px-6">
      <section className="space-y-3">
        {id && (
          <div className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-600 shadow-sm">
            Chat route id: <span className="font-semibold text-zinc-950">{id}</span>
          </div>
        )}
        <ChatPanel {...chat} />
      </section>
      <StatusSidebar {...status} />
    </main>
  );
}
