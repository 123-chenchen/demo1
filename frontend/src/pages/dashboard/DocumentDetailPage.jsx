import React, { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useAppContext } from '../../app/AppContext.jsx';
import { ChatPanel } from '../../components/ChatPanel.jsx';
import { formatBytes, formatStatus, statusClass } from '../../formatters.js';

export function DocumentDetailPage() {
  const { id } = useParams();
  const { documents: documentState, chat } = useAppContext();
  const { documents, onSelectDocument } = documentState;
  const document = documents.find((item) => item.id === id);

  useEffect(() => {
    if (id) {
      onSelectDocument(id);
    }
  }, [id, onSelectDocument]);

  return (
    <main className="mx-auto grid max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[320px_minmax(0,1fr)] lg:px-6">
      <aside className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
        <Link className="text-sm font-semibold text-teal-700 hover:text-teal-800" to="/documents">
          Back to documents
        </Link>
        {document ? (
          <div className="mt-4 space-y-3">
            <h2 className="text-lg font-bold">{document.original_file_name}</h2>
            <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusClass(document.status)}`}>
              {formatStatus(document.status)}
            </span>
            <dl className="space-y-2 text-sm">
              <DetailRow label="Pages" value={document.total_pages || 0} />
              <DetailRow label="Chunks" value={document.total_chunks || 0} />
              <DetailRow label="Size" value={formatBytes(document.file_size_bytes)} />
            </dl>
          </div>
        ) : (
          <p className="mt-4 text-sm text-zinc-500">Document {id} is not loaded in the current workspace.</p>
        )}
      </aside>
      <ChatPanel {...chat} />
    </main>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="font-semibold text-zinc-900">{value}</dd>
    </div>
  );
}
