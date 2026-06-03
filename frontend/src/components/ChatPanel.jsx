import React from 'react';
import { AlertCircle, Bot, Loader2, Send, User } from 'lucide-react';

import { formatStatus, statusClass } from '../formatters.js';

export function ChatPanel({ selectedDocument, error, messages, isAsking, query, chatEndRef, onSubmit, onQueryChange }) {
  return (
    <section className="flex min-h-[680px] flex-col rounded-lg border border-zinc-200 bg-white shadow-sm">
      <div className="border-b border-zinc-200 px-4 py-3">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-zinc-500">Current scope</p>
            <h2 className="truncate text-lg font-bold">{selectedDocument?.original_file_name || 'All available documents'}</h2>
          </div>
          {selectedDocument && (
            <span className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusClass(selectedDocument.status)}`}>
              {formatStatus(selectedDocument.status)}
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-4 flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <AlertCircle className="mt-0.5 shrink-0" size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {isAsking && (
          <div className="flex gap-3">
            <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 text-teal-700">
              <Bot size={18} />
            </div>
            <div className="rounded-lg bg-zinc-100 px-4 py-3 text-sm text-zinc-600">
              <Loader2 className="inline animate-spin" size={16} /> Retrieving relevant passages and generating an answer...
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <form className="border-t border-zinc-200 p-4" onSubmit={onSubmit}>
        <div className="flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-3 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Example: Summarize this document in 5 key points..."
            disabled={isAsking}
          />
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-3 text-sm font-bold text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
            disabled={!query.trim() || isAsking}
          >
            {isAsking ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
            <span className="hidden sm:inline">Send</span>
          </button>
        </div>
      </form>
    </section>
  );
}

function ChatMessage({ message }) {
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
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.sources?.length > 0 && <p className="mt-2 text-xs font-semibold text-zinc-500">{message.sources.length} related sources</p>}
      </div>

      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white">
          <User size={17} />
        </div>
      )}
    </div>
  );
}
