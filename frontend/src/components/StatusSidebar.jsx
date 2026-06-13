import React from 'react';
import { CheckCircle2 } from 'lucide-react';

import { formatStatus } from '../formatters.js';

export function StatusSidebar({ user, selectedNotebook, selectedDocument, lastAnswer }) {
  return (
    <aside className="space-y-4">
      <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="text-emerald-600" size={19} />
          <h2 className="font-bold">Status</h2>
        </div>
        <dl className="mt-4 space-y-3 text-sm">
          <StatusRow label="Account" value={user.email} />
          <StatusRow label="Notebook" value={selectedNotebook?.title || 'Public'} />
          <StatusRow label="Selected document" value={selectedDocument ? formatStatus(selectedDocument.status) : 'None selected'} />
          <StatusRow label="Retriever" value={lastAnswer?.retriever || 'No question yet'} />
          <StatusRow label="Answer model" value={lastAnswer?.generator_model_name || lastAnswer?.generator_provider || 'No question yet'} />
          <StatusRow label="Latency" value={lastAnswer ? `${Math.round(lastAnswer.total_latency_ms)} ms` : 'N/A'} />
        </dl>
      </section>
    </aside>
  );
}

function StatusRow({ label, value }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="text-right font-semibold">{value}</dd>
    </div>
  );
}
