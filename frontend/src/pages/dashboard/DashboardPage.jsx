import React, { useEffect, useMemo, useState } from 'react';

import { useAppContext } from '../../app/AppContext.jsx';
import { ACCESS_TOKEN_KEY, apiFetch } from '../../api.js';
import { ChatPanel } from '../../components/ChatPanel.jsx';
import { DocumentsPanel } from '../../components/DocumentsPanel.jsx';
import { NotebookPanel } from '../../components/NotebookPanel.jsx';
import { PdfCitationViewer } from '../../components/PdfCitationViewer.jsx';
import { ResizableNotebookLayout } from '../../components/ResizableNotebookLayout.jsx';

export function DashboardPage() {
  const { isAuthDisabled, notebooks, documents, chat, header } = useAppContext();
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [viewerDocument, setViewerDocument] = useState(null);
  const selectedDocumentKey = documents.selectedDocumentIds.join('|');
  const viewerDocuments = useMemo(() => {
    const byId = new Map(chat.selectedDocuments.map((document) => [String(document.id), document]));
    if (viewerDocument?.id) byId.set(String(viewerDocument.id), viewerDocument);
    return Array.from(byId.values());
  }, [chat.selectedDocuments, viewerDocument]);

  useEffect(() => {
    setSelectedCitation(null);
    setViewerDocument(null);
  }, [selectedDocumentKey]);

  async function handleSourceSelect(source, sourceNumber) {
    const document = resolveCitationDocument(source, documents.documents, chat.selectedDocument);
    setViewerDocument(document);

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
      setViewerDocument(resolveCitationDocument(resolvedCitation.source, documents.documents, document));
    } catch {
      // Keep the source metadata already returned by the chat response.
    }
  }

  function startNewChat() {
    chat.onNewChat();
    setSelectedCitation(null);
    setViewerDocument(null);
  }

  return (
    <ResizableNotebookLayout
      storageKey={layoutStorageKey(header.user, notebooks.selectedNotebookId)}
      sources={(
        <aside className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto pr-1">
          {!isAuthDisabled && <NotebookPanel {...notebooks} />}
          <DocumentsPanel {...documents} />
        </aside>
      )}
      chat={(
        <ChatPanel
          {...chat}
          onNewChat={startNewChat}
          onSourceSelect={handleSourceSelect}
          selectedSource={selectedCitation?.source}
        />
      )}
      studio={(
        <PdfCitationViewer
          document={viewerDocument || chat.selectedDocument}
          documents={viewerDocuments}
          activeCitation={selectedCitation?.source}
        />
      )}
    />
  );
}

function layoutStorageKey(user, notebookId) {
  return `pdf-chatbot-layout:${user?.email || 'guest'}:${notebookId || 'public'}`;
}

function resolveCitationDocument(source, documents, fallbackDocument) {
  if (!source?.document_id) return fallbackDocument || null;
  const existingDocument = documents.find((item) => String(item.id) === String(source.document_id));
  if (existingDocument) return existingDocument;
  return {
    id: source.document_id,
    original_file_name: source.document_name || source.original_file_name || 'Referenced PDF',
  };
}

function normalizeCitationSource(source, sourceNumber) {
  const normalized = {
    ...source,
    page_number: source.page_number || source.page_from || source.page_to,
    quoted_text: source.quoted_text || source.text || source.content,
  };
  return { source: normalized, sourceNumber };
}
