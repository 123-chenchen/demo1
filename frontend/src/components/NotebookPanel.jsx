import React from 'react';
import { Plus, RefreshCw, Trash2 } from 'lucide-react';

export function NotebookPanel({
  notebooks,
  selectedNotebookId,
  newNotebookTitle,
  isNotebookLoading,
  language = 'en',
  onReload,
  onSelectNotebook,
  onNewNotebookTitleChange,
  onCreateNotebook,
  onDeleteNotebook,
}) {
  const text = language === 'vi' ? viText : enText;
  const selectedNotebook = notebooks.find((notebook) => notebook.id === selectedNotebookId);

  function confirmDeleteNotebook() {
    if (!selectedNotebook || !onDeleteNotebook) return;
    const name = selectedNotebook.title || text.untitledNotebook;
    if (window.confirm(`${text.deleteNotebookConfirm} "${name}"?`)) {
      onDeleteNotebook(selectedNotebook.id);
    }
  }

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-bold">Notebook</h2>
          <p className="text-sm text-zinc-500">{notebooks.length} {text.personalWorkspaces}</p>
        </div>
        <button
          className="rounded-lg border border-zinc-200 p-2 text-zinc-600 hover:bg-zinc-50"
          onClick={onReload}
          disabled={isNotebookLoading}
          aria-label={text.reloadNotebooks}
        >
          <RefreshCw size={18} className={isNotebookLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="mt-4 flex gap-2">
        <select
          className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
          value={selectedNotebookId}
          onChange={(event) => onSelectNotebook(event.target.value)}
        >
          {notebooks.map((notebook) => (
            <option key={notebook.id} value={notebook.id}>
              {notebook.title || text.untitledNotebook}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-rose-200 bg-white text-rose-600 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-40"
          onClick={confirmDeleteNotebook}
          disabled={!selectedNotebook || isNotebookLoading}
          aria-label={text.deleteNotebook}
          title={text.deleteNotebook}
        >
          <Trash2 size={17} />
        </button>
      </div>

      <form className="mt-3 flex gap-2" onSubmit={onCreateNotebook}>
        <input
          className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
          value={newNotebookTitle}
          onChange={(event) => onNewNotebookTitleChange(event.target.value)}
          placeholder={text.newNotebook}
        />
        <button className="rounded-lg bg-zinc-950 p-2 text-white disabled:bg-zinc-300" disabled={!newNotebookTitle.trim()}>
          <Plus size={18} />
        </button>
      </form>
    </section>
  );
}

const enText = {
  personalWorkspaces: 'personal workspaces',
  reloadNotebooks: 'Reload notebooks',
  deleteNotebook: 'Delete notebook',
  deleteNotebookConfirm: 'Delete notebook',
  untitledNotebook: 'Untitled notebook',
  newNotebook: 'New notebook',
};

const viText = {
  deleteNotebook: 'Xóa notebook',
  deleteNotebookConfirm: 'Xóa notebook',
  personalWorkspaces: 'không gian làm việc cá nhân',
  reloadNotebooks: 'Tải lại notebook',
  untitledNotebook: 'Notebook chưa đặt tên',
  newNotebook: 'Notebook mới',
};
