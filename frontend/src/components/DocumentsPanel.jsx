import React from 'react';
import { FileText, Loader2, RefreshCw, Search, UploadCloud } from 'lucide-react';

import { formatBytes, formatStatus, statusClass } from '../formatters.js';

export function DocumentsPanel({
  documents,
  filteredDocuments,
  selectedDocumentId,
  selectedNotebook,
  search,
  isLoadingDocuments,
  isUploading,
  fileInputRef,
  onReload,
  onUpload,
  onSearchChange,
  onSelectDocument,
}) {
  return (
    <>
      <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-bold">PDF Documents</h2>
            <p className="text-sm text-zinc-500">
              {documents.length} file {selectedNotebook ? `in ${selectedNotebook.title || 'notebook'}` : 'public'}
            </p>
          </div>
          <button
            className="rounded-lg border border-zinc-200 p-2 text-zinc-600 hover:bg-zinc-50"
            onClick={onReload}
            disabled={isLoadingDocuments}
            aria-label="Reload documents"
          >
            <RefreshCw size={18} className={isLoadingDocuments ? 'animate-spin' : ''} />
          </button>
        </div>

        <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-teal-300 bg-teal-50 px-4 py-6 text-center hover:bg-teal-100">
          {isUploading ? <Loader2 className="animate-spin text-teal-700" size={26} /> : <UploadCloud className="text-teal-700" size={28} />}
          <span className="mt-2 text-sm font-semibold text-teal-900">{isUploading ? 'Uploading and processing...' : 'Choose a PDF to upload'}</span>
          <span className="mt-1 text-xs text-teal-700">The backend will store, extract, chunk, and index vectors</span>
          <input
            ref={fileInputRef}
            className="hidden"
            type="file"
            accept="application/pdf,.pdf"
            disabled={isUploading}
            onChange={(event) => onUpload(event.target.files?.[0])}
          />
        </label>

        <div className="relative mt-4">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={17} />
          <input
            className="w-full rounded-lg border border-zinc-200 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search files..."
          />
        </div>
      </section>

      <section className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
        {filteredDocuments.map((document) => (
          <DocumentListItem
            key={document.id}
            document={document}
            isSelected={selectedDocumentId === document.id}
            onSelect={() => onSelectDocument(document.id)}
          />
        ))}

        {!isLoadingDocuments && filteredDocuments.length === 0 && (
          <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-500">No PDFs yet. Upload a file to get started.</div>
        )}
      </section>
    </>
  );
}

function DocumentListItem({ document, isSelected, onSelect }) {
  return (
    <button
      className={`w-full rounded-lg border p-3 text-left shadow-sm transition ${
        isSelected ? 'border-teal-500 bg-white ring-4 ring-teal-100' : 'border-zinc-200 bg-white hover:border-zinc-300'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-lg bg-zinc-100 p-2 text-zinc-700">
          <FileText size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{document.original_file_name}</p>
          <p className="mt-1 text-xs text-zinc-500">
            {document.total_pages || 0} pages · {document.total_chunks || 0} chunks · {formatBytes(document.file_size_bytes)}
          </p>
          <span className={`mt-2 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${statusClass(document.status)}`}>
            {formatStatus(document.status)}
          </span>
        </div>
      </div>
    </button>
  );
}
