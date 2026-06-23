import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useAppContext } from '../../app/AppContext.jsx';
import { ChatPanel } from '../../components/ChatPanel.jsx';
import { PdfCitationViewer } from '../../components/PdfCitationViewer.jsx';
import { ACCESS_TOKEN_KEY, apiFetch } from '../../api.js';
import { displayDocumentTitle } from '../../documentTitles.js';
import { formatBytes, formatStatus, statusClass } from '../../formatters.js';

export function DocumentDetailPage() {
  const { id } = useParams();
  const { documents: documentState, chat } = useAppContext();
  const { documents, onSelectDocument } = documentState;
  const document = documents.find((item) => item.id === id);
  const [selectedCitation, setSelectedCitation] = useState(null);

  useEffect(() => {
    if (id) {
      onSelectDocument(id);
    }
  }, [id, onSelectDocument]);

  useEffect(() => {
    setSelectedCitation(null);
  }, [id]);

  async function handleSourceSelect(source, sourceNumber) {
    const fallbackCitation = normalizeCitationSource(source, sourceNumber);
    setSelectedCitation(fallbackCitation);

    if (!source?.document_id || !source?.chunk_id) return;
    try {
      const citation = await apiFetch(
        `/api/documents/${source.document_id}/citation/${source.chunk_id}`,
        {},
        localStorage.getItem(ACCESS_TOKEN_KEY) || ''
      );
      const resolvedCitation = normalizeCitationSource({ ...source, ...citation }, sourceNumber);
      setSelectedCitation(resolvedCitation);
    } catch {
      // Keep the citation data already returned by the chat response.
    }
  }

  return (
    <main className="mx-auto grid max-w-[1600px] gap-4 px-4 py-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(420px,0.9fr)] lg:px-6">
      <section className="space-y-4">
        <aside className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
          <Link className="text-sm font-semibold text-teal-700 hover:text-teal-800" to="/documents">
            Back to documents
          </Link>
          {document ? (
            <div className="mt-4 space-y-3">
              <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-bold">{displayDocumentTitle(document)}</h2>
                  <p className="mt-1 text-sm text-zinc-500">Original PDF preview and citation target</p>
                </div>
                <span className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusClass(document.status)}`}>
                  {formatStatus(document.status)}
                </span>
              </div>
              <dl className="grid gap-2 text-sm sm:grid-cols-3">
                <DetailRow label="Pages" value={document.total_pages || 0} />
                <DetailRow label="Text sections" value={document.total_chunks || 0} />
                <DetailRow label="Size" value={formatBytes(document.file_size_bytes)} />
              </dl>
            </div>
          ) : (
            <p className="mt-4 text-sm text-zinc-500">Document {id} is not loaded in the current workspace.</p>
          )}
        </aside>

        <PdfCitationViewer
          document={document}
          activeCitation={selectedCitation?.source}
        />
      </section>

      <ChatPanel
        {...chat}
        onSourceSelect={handleSourceSelect}
        selectedSource={selectedCitation?.source}
      />
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

function normalizeCitationSource(source, sourceNumber) {
  const normalized = {
    ...source,
    page_number: source.page_number || source.page_from || source.page_to,
    quoted_text: source.quoted_text || source.text || source.content,
  };
  return { source: normalized, sourceNumber };
}
