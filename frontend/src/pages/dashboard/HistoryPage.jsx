import React from 'react';
import { MessageSquareText, Trash2 } from 'lucide-react';

import { useAppContext } from '../../app/AppContext.jsx';

export function HistoryPage() {
  const { history } = useAppContext();
  const visibleMessages = history.messages.filter((message) => message.id !== 'welcome');
  const isVietnamese = history.language === 'vi';
  const text = isVietnamese ? viText : enText;

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
          {visibleMessages.map((message) => (
            <article
              key={message.id}
              className={`max-w-3xl rounded-lg px-4 py-3 text-sm leading-6 ${
                message.role === 'user' ? 'ml-auto bg-zinc-950 text-white' : 'bg-zinc-100 text-zinc-900'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              {message.sources?.length > 0 && (
                <p className="mt-2 text-xs font-semibold text-zinc-500">{message.sources.length} {text.relatedSources}</p>
              )}
            </article>
          ))}

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

const enText = {
  history: 'History',
  savedChats: 'saved chats',
  untitledChat: 'Untitled chat',
  noHistory: 'No saved chat history yet.',
  conversation: 'Conversation',
  relatedSources: 'related sources',
  selectChat: 'Select a saved chat to view its messages.',
  deleteChat: 'Delete chat',
  deleteChatConfirm: 'Delete chat',
};

const viText = {
  deleteChat: 'Xóa chat',
  deleteChatConfirm: 'Xóa chat',
  history: 'Lịch sử',
  savedChats: 'cuộc chat đã lưu',
  untitledChat: 'Cuộc chat chưa đặt tên',
  noHistory: 'Chưa có lịch sử chat đã lưu.',
  conversation: 'Nội dung cuộc trò chuyện',
  relatedSources: 'nguồn liên quan',
  selectChat: 'Chọn một cuộc chat đã lưu để xem nội dung.',
};
