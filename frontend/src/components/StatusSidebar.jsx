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

      <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
        <h2 className="font-bold">Cited Sources</h2>
        <div className="mt-3 max-h-[560px] space-y-3 overflow-y-auto pr-1">
          {(lastAnswer?.sources || []).map((source, index) => (
            <article key={`${source.chunk_id}-${index}`} className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-semibold">{source.original_file_name}</p>
                <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-zinc-600 ring-1 ring-zinc-200">#{index + 1}</span>
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                Page {source.page_from || '?'}
                {source.page_to && source.page_to !== source.page_from ? `-${source.page_to}` : ''} · chunk {source.chunk_index}
              </p>
              <p className="mt-2 line-clamp-5 text-sm leading-6 text-zinc-700">{source.content}</p>
            </article>
          ))}

          {!lastAnswer?.sources?.length && <p className="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-500">Related sources will appear after the chatbot answers.</p>}
        </div>
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
