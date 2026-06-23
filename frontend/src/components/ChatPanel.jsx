import React from 'react';
import { AlertCircle, Bot, CheckCircle2, FileQuestion, FileText, Loader2, Plus, Send, User } from 'lucide-react';

import { displayDocumentTitle, displayDocumentTopic, displayOriginalFileName } from '../documentTitles.js';
import { formatStatus, statusClass } from '../formatters.js';

export function ChatPanel({
  selectedDocument,
  selectedDocuments = [],
  readySelectedDocuments = [],
  scopeLabel,
  suggestionTitle,
  suggestedQuestions = [],
  isLoadingSuggestions = false,
  hasReadyScope = false,
  language = 'en',
  error,
  messages,
  isAsking,
  query,
  chatEndRef,
  onSubmit,
  onQueryChange,
  onSuggestionSelect,
  onNewChat,
  onSourceSelect,
  selectedSource,
}) {
  const visibleMessages = messages.filter((message) => message.id !== 'welcome');
  const hasUserMessages = visibleMessages.some((message) => message.role === 'user');
  const showSuggestions = hasReadyScope && !hasUserMessages;
  const text = language === 'vi'
    ? { ...viText, answering: 'Đang tìm nội dung liên quan và tạo câu trả lời...' }
    : enText;
  const headerTopic = suggestionTitle || buildHeaderTopic(selectedDocuments, selectedDocument, text);

  return (
    <section className="flex h-full min-h-0 flex-col rounded-lg border border-zinc-200 bg-white shadow-sm">
      <div className="border-b border-zinc-200 px-4 py-3">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-bold">{headerTopic}</h2>
            <SourceScopeList documents={selectedDocuments} language={language} />
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {readySelectedDocuments.length > 0 && (
              <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-100">
                <CheckCircle2 size={13} />
                {text.ready}
              </span>
            )}
            {!readySelectedDocuments.length && selectedDocuments.length === 1 && selectedDocument && (
              <span className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusClass(selectedDocument.status)}`}>
                {formatStatus(selectedDocument.status)}
              </span>
            )}
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-bold text-zinc-700 hover:border-teal-300 hover:text-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={onNewChat}
              disabled={isAsking}
            >
              <Plus size={16} />
              {text.newChat}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-4 flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <AlertCircle className="mt-0.5 shrink-0" size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {visibleMessages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            language={language}
            onSourceSelect={onSourceSelect}
            selectedSource={selectedSource}
          />
        ))}

        {isAsking && (
          <div className="flex gap-3">
            <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 text-teal-700">
              <Bot size={18} />
            </div>
            <div className="rounded-lg bg-zinc-100 px-4 py-3 text-sm text-zinc-600">
              <Loader2 className="inline animate-spin" size={16} /> {text.answering}
            </div>
          </div>
        )}

        {showSuggestions && (
          <SuggestedQuestions
            title={suggestionTitle}
            questions={suggestedQuestions}
            isLoading={isLoadingSuggestions}
            isDisabled={isAsking}
            language={language}
            onSelect={onSuggestionSelect}
          />
        )}

        {!showSuggestions && !visibleMessages.length && !selectedDocuments.length && (
          <ChatEmptyState
            title={text.addSourcesTitle}
            body={text.addSourcesBody}
          />
        )}

        {!showSuggestions && !visibleMessages.length && selectedDocuments.length > 0 && !hasReadyScope && (
          <ChatEmptyState
            title={text.processingTitle}
            body={text.processingBody}
          />
        )}

        <div ref={chatEndRef} />
      </div>

      <form className="border-t border-zinc-200 p-4" onSubmit={onSubmit}>
        <div className="flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-3 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder={text.askPlaceholder}
            disabled={isAsking}
          />
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-3 text-sm font-bold text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
            disabled={!query.trim() || isAsking}
          >
            {isAsking ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
            <span className="hidden sm:inline">{text.send}</span>
          </button>
        </div>
      </form>
    </section>
  );
}

function SourceScopeList({ documents, language }) {
  if (!documents.length) {
    return <p className="mt-1 text-xs text-zinc-500">{language === 'vi' ? 'Chưa chọn nguồn nào' : 'No selected sources'}</p>;
  }

  return (
    <div className="mt-2 flex max-h-16 flex-wrap gap-1.5 overflow-y-auto pr-1">
      {documents.map((document) => (
        <span
          key={document.id}
          className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs font-semibold text-zinc-600"
          title={displayOriginalFileName(document)}
        >
          <FileText size={12} />
          <span className="max-w-[180px] truncate">{displayOriginalFileName(document)}</span>
          <span className={`h-1.5 w-1.5 rounded-full ${document.status === 'processed' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
        </span>
      ))}
    </div>
  );
}

function buildHeaderTopic(selectedDocuments, selectedDocument, text) {
  if (selectedDocuments.length > 1) {
    const topics = selectedDocuments.map(displayDocumentTopic).filter(Boolean);
    return topics.length ? topics.slice(0, 2).join(' / ') : `${text.selectedFiles} (${selectedDocuments.length})`;
  }
  return displayDocumentTopic(selectedDocuments[0] || selectedDocument) || displayDocumentTitle(selectedDocument) || text.noFilesSelected;
}

function SuggestedQuestions({ title, questions, isLoading, isDisabled, language, onSelect }) {
  const emptyText = language === 'vi'
    ? 'Chưa có câu hỏi gợi ý dựa trên nội dung.'
    : 'No content-based suggestions are available yet.';
  const heading = language === 'vi' ? 'Câu hỏi gợi ý' : 'Suggested questions';

  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase text-zinc-500">{heading}</p>
          {title && <h3 className="truncate text-sm font-bold text-zinc-900">{title}</h3>}
        </div>
        {isLoading && <Loader2 className="shrink-0 animate-spin text-zinc-500" size={16} />}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {isLoading
          ? Array.from({ length: 5 }, (_, index) => (
              <div key={index} className="h-12 rounded-lg border border-zinc-200 bg-white" />
            ))
          : questions.length === 0
            ? (
                <p className="rounded-lg border border-zinc-200 bg-white px-3 py-3 text-sm text-zinc-500 sm:col-span-2">
                  {emptyText}
                </p>
              )
            : questions.map((question) => (
                <button
                  key={question}
                  type="button"
                  className="rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-left text-sm font-semibold leading-5 text-zinc-700 shadow-sm hover:border-teal-300 hover:bg-teal-50 hover:text-teal-900"
                  onClick={() => onSelect?.(question)}
                  disabled={isDisabled}
                >
                  {question}
                </button>
              ))}
      </div>
    </div>
  );
}

function ChatEmptyState({ title, body }) {
  return (
    <div className="flex min-h-[360px] items-center justify-center rounded-lg border border-dashed border-zinc-200 bg-zinc-50 p-6 text-center">
      <div className="max-w-sm">
        <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-white text-zinc-700 shadow-sm">
          <FileQuestion size={22} />
        </div>
        <h3 className="mt-4 text-base font-bold text-zinc-950">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-zinc-500">{body}</p>
      </div>
    </div>
  );
}

function ChatMessage({ message, language, onSourceSelect, selectedSource }) {
  const isUser = message.role === 'user';
  const bubbleClass = isUser
    ? 'bg-zinc-950 text-white'
    : message.isError
      ? 'bg-rose-50 text-rose-900'
      : 'bg-zinc-100 text-zinc-900';

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${message.isError ? 'bg-rose-100 text-rose-700' : 'bg-teal-100 text-teal-700'}`}>
          <Bot size={18} />
        </div>
      )}

      <div className={`max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6 ${bubbleClass}`}>
        <p className="whitespace-pre-wrap">
          {isUser ? message.content : renderCitedAnswer(message.content, message.sources, onSourceSelect)}
        </p>
        {!isUser && message.sources?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.sources.map((source, index) => {
              const sourceNumber = index + 1;
              const pageLabel = formatPageLabel(source, language);
              const isSelected = selectedSource?.chunk_id === source.chunk_id;
              const sourceTitle = displayDocumentTitle(source);
              return (
                <button
                  key={source.chunk_id || `${source.document_id}-${source.chunk_index}-${index}`}
                  type="button"
                  className={`inline-flex max-w-full items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-semibold transition ${
                    isSelected
                      ? 'border-teal-500 bg-teal-50 text-teal-800'
                      : 'border-zinc-200 bg-white text-zinc-600 hover:border-teal-300 hover:text-teal-800'
                  }`}
                  onClick={() => onSourceSelect?.(source, sourceNumber)}
                  title={`${sourceTitle} / ${pageLabel}`}
                >
                  <FileText size={13} />
                  [{sourceNumber}] {sourceTitle} / {pageLabel}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white">
          <User size={17} />
        </div>
      )}
    </div>
  );
}

function renderCitedAnswer(content, sources = [], onSourceSelect) {
  if (!content || !sources.length) return content;

  const parts = [];
  const pattern = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(content)) !== null) {
    const sourceNumber = Number(match[1]);
    const source = sources[sourceNumber - 1];
    if (!source) continue;

    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }

    parts.push(
      <button
        key={`${match.index}-${sourceNumber}`}
        type="button"
        className="mx-0.5 inline-flex rounded bg-teal-50 px-1.5 py-0.5 text-xs font-bold text-teal-800 ring-1 ring-teal-200 hover:bg-teal-100"
        onClick={() => onSourceSelect?.(source, sourceNumber)}
        title={displayDocumentTitle(source)}
      >
        [{sourceNumber}]
      </button>
    );
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.length ? parts : content;
}

function formatPageLabel(source, language) {
  const sectionLabel = language === 'vi' ? 'mục' : 'section';
  const text = language === 'vi'
    ? { page: 'trang', pages: 'trang' }
    : { page: 'page', pages: 'pages' };

  if (source?.page_number) return `${text.page} ${source.page_number}`;
  if (!source?.page_from && !source?.page_to) return `${sectionLabel} ${source?.chunk_index ?? '-'}`;
  if (source.page_from && source.page_to && source.page_from !== source.page_to) {
    return `${text.pages} ${source.page_from}-${source.page_to}`;
  }
  return `${text.page} ${source.page_from || source.page_to}`;
}

const enText = {
  noFilesSelected: 'No files selected',
  ready: 'Ready',
  newChat: 'New Chat',
  answering: 'Retrieving relevant passages and generating an answer...',
  addSourcesTitle: 'Add sources to begin',
  addSourcesBody: 'Upload PDFs from the Sources panel. Once a source is ready, content-based suggested questions will appear here.',
  processingTitle: 'Sources are processing',
  processingBody: 'Chat will be ready when at least one selected PDF reaches Ready status.',
  askPlaceholder: 'Ask about the selected PDFs...',
  send: 'Send',
  selectedFiles: 'Selected PDFs',
};

const viText = {
  selectedFiles: 'PDF đã chọn',
  noFilesSelected: 'Chưa chọn tệp',
  ready: 'Sẵn sàng',
  newChat: 'Chat mới',
  answering: 'Đang tìm đoạn liên quan và tạo câu trả lời...',
  addSourcesTitle: 'Thêm nguồn để bắt đầu',
  addSourcesBody: 'Tải PDF lên từ cột Sources. Khi tài liệu sẵn sàng, câu hỏi gợi ý dựa trên nội dung sẽ xuất hiện ở đây.',
  processingTitle: 'Nguồn đang được xử lý',
  processingBody: 'Chat sẽ sẵn sàng khi ít nhất một PDF đã chọn chuyển sang trạng thái Ready.',
  askPlaceholder: 'Hỏi về các PDF đã chọn...',
  send: 'Gửi',
};
