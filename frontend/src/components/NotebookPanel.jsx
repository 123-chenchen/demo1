import React from 'react';
import { Plus, RefreshCw } from 'lucide-react';

export function NotebookPanel({
  notebooks,
  selectedNotebookId,
  newNotebookTitle,
  isNotebookLoading,
  onReload,
  onSelectNotebook,
  onNewNotebookTitleChange,
  onCreateNotebook,
}) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-bold">Notebook</h2>
          <p className="text-sm text-zinc-500">{notebooks.length} personal workspaces</p>
        </div>
        <button
          className="rounded-lg border border-zinc-200 p-2 text-zinc-600 hover:bg-zinc-50"
          onClick={onReload}
          disabled={isNotebookLoading}
          aria-label="Reload notebooks"
        >
          <RefreshCw size={18} className={isNotebookLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      <select
        className="mt-4 w-full rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
        value={selectedNotebookId}
        onChange={(event) => onSelectNotebook(event.target.value)}
      >
        {notebooks.map((notebook) => (
          <option key={notebook.id} value={notebook.id}>
            {notebook.title || 'Untitled notebook'}
          </option>
        ))}
      </select>

      <form className="mt-3 flex gap-2" onSubmit={onCreateNotebook}>
        <input
          className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
          value={newNotebookTitle}
          onChange={(event) => onNewNotebookTitleChange(event.target.value)}
          placeholder="New notebook"
        />
        <button className="rounded-lg bg-zinc-950 p-2 text-white disabled:bg-zinc-300" disabled={!newNotebookTitle.trim()}>
          <Plus size={18} />
        </button>
      </form>
    </section>
  );
}
