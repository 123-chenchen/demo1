import React from 'react';

import { useAppContext } from '../../app/AppContext.jsx';

export function AnalyticsPage() {
  const { documents, chat } = useAppContext();

  return (
    <main className="mx-auto grid max-w-5xl gap-4 px-4 py-4 sm:grid-cols-3 lg:px-6">
      <MetricCard label="Documents" value={documents.documents.length} />
      <MetricCard label="Visible files" value={documents.filteredDocuments.length} />
      <MetricCard label="Messages" value={chat.messages.length} />
    </main>
  );
}

function MetricCard({ label, value }) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-semibold text-zinc-500">{label}</p>
      <p className="mt-2 text-3xl font-bold text-zinc-950">{value}</p>
    </section>
  );
}
