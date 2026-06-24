import React from 'react';
import { FileText, MessageSquareText, Trash2 } from 'lucide-react';

import { useAppContext } from '../../app/AppContext.jsx';

export function HistoryPage() {
  const { history } = useAppContext();
  const visibleMessages = history.messages.filter((message) => message.id !== 'welcome');
  const text = enText;

  async function openSession(sessionId) {
    await history.onSelectSession(sessionId);
  }

  async function deleteSession(session) {
    if (!window.confirm(`${text.deleteChatConfirm} "${session.title || text.untitledChat}"?`)) return;
    await history.onDeleteSession?.(session.id);
  }

  return (
    <main className="grid min-h-[calc(100vh-154px)] w-full gap-4 px-4 py-4 lg:grid-cols-[380px_minmax(0,1fr)] lg:px-6">
      <section className="min-h-0 rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-3 border-b border-zinc-200 px-4 py-3">
          <div>
            <h2 className="text-lg font-bold">{text.history}</h2>
            <p className="text-sm text-zinc-500">{history.sessions.length} {text.savedChats}</p>
          </div>
        </div>

        <div className="max-h-[calc(100vh-220px)] space-y-2 overflow-y-auto p-3">
          {history.sessions.map((session) => {
            const isActive = session.id === history.activeSessionId;
            const fileNames = fileNamesFromMetadata(session.metadata);
            return (
              <article
                key={session.id}
                className={`w-full rounded-lg border p-3 text-left transition ${
                  isActive ? 'border-teal-500 bg-teal-50 ring-4 ring-teal-100' : 'border-zinc-200 bg-white hover:border-zinc-300'
                }`}
              >
                <div className="flex items-start gap-3">
                  <button type="button" className="flex min-w-0 flex-1 items-start gap-3 text-left" onClick={() => openSession(session.id)}>
                    <div className="rounded-lg bg-zinc-100 p-2 text-zinc-700">
                      <MessageSquareText size={17} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-zinc-950">{session.title || text.untitledChat}</p>
                      {fileNames.length > 0 && (
                        <p className="mt-1 flex items-center gap-1 truncate text-xs font-medium text-teal-700" title={fileNames.join(' / ')}>
                          <FileText size={12} />
                          <span className="truncate">{fileNames.join(' / ')}</span>
                        </p>
                      )}
                      <p className="mt-1 text-xs text-zinc-500">{formatDate(session.updated_at || session.created_at)}</p>
                    </div>
                  </button>
                  <button
                    type="button"
                    className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-rose-200 bg-white text-rose-600 hover:bg-rose-50"
                    onClick={() => deleteSession(session)}
                    aria-label={text.deleteChat}
                    title={text.deleteChat}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </article>
            );
          })}

          {!history.isLoading && history.sessions.length === 0 && (
            <p className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-500">{text.noHistory}</p>
          )}
        </div>
      </section>

      <section className="flex min-h-0 flex-col rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="border-b border-zinc-200 px-4 py-3">
          <h3 className="text-lg font-bold">{text.conversation}</h3>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {visibleMessages.map((message) => {
            const fileNames = fileNamesFromMessage(message);
            const isUser = message.role === 'user';
            return (
              <article
                key={message.id}
                className={`max-w-3xl rounded-lg px-4 py-3 text-sm leading-6 ${ 
                  isUser ? 'ml-auto bg-zinc-950 text-white' : 'bg-zinc-100 text-zinc-900'
                }`}
              >
                {isUser && fileNames.length > 0 && (
                  <p className="mb-2 flex items-center gap-1 text-xs font-semibold text-teal-200" title={fileNames.join(' / ')}>
                    <FileText size={13} />
                    <span className="truncate">{text.askedIn} {fileNames.join(' / ')}</span>
                  </p>
                )}
                <p className="whitespace-pre-wrap">{message.content}</p>
                {message.sources?.length > 0 && (
                  <p className="mt-2 text-xs font-semibold text-zinc-500">{message.sources.length} {text.relatedSources}</p>
                )}
              </article>
            );
          })}

          {!history.isLoading && visibleMessages.length === 0 && (
            <p className="text-sm text-zinc-500">{text.selectChat}</p>
          )}
        </div>
      </section>
    </main>
  );
}

function formatDate(value) {
  if (!value) return 'Unknown time';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function fileNamesFromMessage(message) {
  return uniqueNames([
    ...fileNamesFromMetadata(message?.metadata),
    ...(message?.sources || []).map((source) => source.original_file_name || source.document_name),
  ]);
}

function fileNamesFromMetadata(metadata) {
  const names = Array.isArray(metadata?.document_names) ? metadata.document_names : [];
  return uniqueNames([
    ...names,
    metadata?.document_name,
  ]);
}

function uniqueNames(values) {
  return values
    .filter((value) => typeof value === 'string' && value.trim())
    .map((value) => value.trim())
    .filter((value, index, array) => array.indexOf(value) === index);
}

const enText = {
  history: 'History',
  savedChats: 'saved chats',
  untitledChat: 'Untitled chat',
  noHistory: 'No saved chat history yet.',
  conversation: 'Conversation',
  askedIn: 'Asked in',
  relatedSources: 'related sources',
  selectChat: 'Select a saved chat to view its messages.',
  deleteChat: 'Delete chat',
  deleteChatConfirm: 'Delete chat',
};
