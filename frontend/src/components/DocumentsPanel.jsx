import React from 'react';
import { FileText, Loader2, RefreshCw, Search, Trash2, UploadCloud } from 'lucide-react';

import { displayDocumentTitle, displayDocumentTopic, displayOriginalFileName } from '../documentTitles.js';
import { formatBytes, formatStatus, statusClass } from '../formatters.js';

export function DocumentsPanel({
  documents,
  filteredDocuments,
  selectedDocumentId,
  selectedDocumentIds = [],
  selectedNotebook,
  search,
  isLoadingDocuments,
  isUploading,
  language = 'en',
  fileInputRef,
  onReload,
  onUpload,
  onSearchChange,
  onSelectDocument,
  onToggleDocumentScope,
  onDeleteDocument,
}) {
  const text = language === 'vi' ? viText : enText;

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-bold">{text.sources}</h2>
            <p className="text-sm text-zinc-500">
              {documents.length} PDF {selectedNotebook ? `${text.inNotebook} ${selectedNotebook.title || text.notebook}` : text.public} / {selectedDocumentIds.length} {text.selected}
            </p>
          </div>
          <button
            className="rounded-lg border border-zinc-200 p-2 text-zinc-600 hover:bg-zinc-50"
            onClick={onReload}
            disabled={isLoadingDocuments}
            aria-label={text.reloadDocuments}
          >
            <RefreshCw size={18} className={isLoadingDocuments ? 'animate-spin' : ''} />
          </button>
        </div>

        <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-teal-300 bg-teal-50 px-4 py-5 text-center hover:bg-teal-100">
          {isUploading ? <Loader2 className="animate-spin text-teal-700" size={26} /> : <UploadCloud className="text-teal-700" size={28} />}
          <span className="mt-2 text-sm font-semibold text-teal-900">{isUploading ? text.uploading : text.uploadPdf}</span>
          <input
            ref={fileInputRef}
            className="hidden"
            type="file"
            multiple
            accept="application/pdf,.pdf"
            disabled={isUploading}
            onChange={(event) => onUpload(Array.from(event.target.files || []))}
          />
        </label>

        <div className="relative mt-4">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={17} />
          <input
            className="w-full rounded-lg border border-zinc-200 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={text.searchFiles}
          />
        </div>
      </section>

      <section className="space-y-2 pr-1">
        {filteredDocuments.map((document) => (
          <DocumentListItem
            key={document.id}
            document={document}
            isFocused={selectedDocumentId === document.id}
            isInScope={selectedDocumentIds.includes(document.id)}
            language={language}
            onSelect={() => onSelectDocument(document.id)}
            onToggleScope={() => onToggleDocumentScope(document.id)}
            onDelete={() => onDeleteDocument?.(document.id)}
          />
        ))}

        {!isLoadingDocuments && filteredDocuments.length === 0 && (
          <div className="rounded-lg border border-dashed border-zinc-200 bg-white p-5 text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700">
              <FileText size={20} />
            </div>
            <h3 className="mt-3 text-sm font-bold text-zinc-950">{text.noSources}</h3>
            <p className="mt-1 text-sm leading-6 text-zinc-500">
              {text.noSourcesBody}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function DocumentListItem({ document, isFocused, isInScope, language, onSelect, onToggleScope, onDelete }) {
  const text = language === 'vi' ? viText : enText;
  const topic = displayDocumentTopic(document) || displayDocumentTitle(document);
  const originalFileName = displayOriginalFileName(document) || topic;

  function confirmDelete(event) {
    event.stopPropagation();
    if (window.confirm(`${text.deleteFileConfirm} "${originalFileName}"?`)) {
      onDelete?.();
    }
  }

  return (
    <article
      className={`w-full rounded-lg border bg-white p-3 text-left shadow-sm transition ${
        isInScope
          ? 'border-teal-500 ring-4 ring-teal-100'
          : isFocused
            ? 'border-zinc-300'
            : 'border-zinc-200 hover:border-zinc-300'
      }`}
    >
      <div className="flex items-start gap-3">
        <input
          className="mt-2 h-4 w-4 shrink-0 rounded border-zinc-300 text-teal-600 focus:ring-teal-500"
          type="checkbox"
          checked={isInScope}
          onChange={onToggleScope}
          aria-label={`${text.useInScope} ${displayDocumentTitle(document)}`}
        />
        <button type="button" className="flex min-w-0 flex-1 items-start gap-3 text-left" onClick={onSelect}>
          <div className="mt-0.5 rounded-lg bg-zinc-100 p-2 text-zinc-700">
            <FileText size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{topic}</p>
            <p className="mt-0.5 truncate text-xs font-medium text-zinc-500" title={originalFileName}>{originalFileName}</p>
            <p className="mt-1 text-xs text-zinc-500">
              {document.total_pages || 0} {text.pages} / {document.total_chunks || 0} {text.sections} / {formatBytes(document.file_size_bytes)}
            </p>
            <span className={`mt-2 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${statusClass(document.status)}`}>
              {formatStatus(document.status)}
            </span>
          </div>
        </button>
        <button
          type="button"
          className="mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-rose-200 bg-white text-rose-600 hover:bg-rose-50"
          onClick={confirmDelete}
          aria-label={text.deleteFile}
          title={text.deleteFile}
        >
          <Trash2 size={15} />
        </button>
      </div>
    </article>
  );
}

const enText = {
  sources: 'Sources',
  inNotebook: 'in',
  notebook: 'notebook',
  public: 'public',
  selected: 'selected',
  reloadDocuments: 'Reload documents',
  uploading: 'Uploading and processing...',
  uploadPdf: 'Upload PDF files',
  searchFiles: 'Search files...',
  noSources: 'No sources yet',
  noSourcesBody: 'Upload one or more PDFs. Ready files can be selected together for notebook-wide questions.',
  useInScope: 'Use in chat scope:',
  deleteFile: 'Delete PDF',
  deleteFileConfirm: 'Delete PDF',
  pages: 'pages',
  sections: 'text sections',
};

const viText = {
  deleteFile: 'Xóa PDF',
  deleteFileConfirm: 'Xóa PDF',
  sections: 'mục nội dung',
  sources: 'Nguồn',
  inNotebook: 'trong',
  notebook: 'notebook',
  public: 'công khai',
  selected: 'đã chọn',
  reloadDocuments: 'Tải lại tài liệu',
  uploading: 'Đang tải lên và xử lý...',
  uploadPdf: 'Tải PDF lên',
  searchFiles: 'Tìm tài liệu...',
  noSources: 'Chưa có nguồn',
  noSourcesBody: 'Tải lên một hoặc nhiều PDF. Các tệp Ready có thể được chọn cùng lúc để hỏi theo phạm vi notebook.',
  useInScope: 'Dùng trong phạm vi chat:',
  pages: 'trang',
};
