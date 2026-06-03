import React from 'react';

import { useAppContext } from '../../app/AppContext.jsx';

export function HistoryPage() {
  const { chat } = useAppContext();
  const userMessages = chat.messages.filter((message) => message.role === 'user');

  return (
    <main className="mx-auto max-w-4xl px-4 py-4 lg:px-6">
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">History</h2>
        <div className="mt-4 space-y-2">
          {userMessages.map((message) => (
            <article key={message.id} className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-sm">
              {message.content}
            </article>
          ))}
          {userMessages.length === 0 && <p className="text-sm text-zinc-500">No questions asked in this session.</p>}
        </div>
      </section>
    </main>
  );
}
