import React, { useState } from 'react';
import { ChevronDown, Plus, Trash2 } from 'lucide-react';

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
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const text = enText;
  const selectedNotebook = notebooks.find((notebook) => notebook.id === selectedNotebookId);

  async function confirmDeleteNotebook(event, notebook) {
    event.stopPropagation();
    if (!notebook || !onDeleteNotebook) return;

    const name = notebook.title || text.untitledNotebook;
    if (window.confirm(`${text.deleteNotebookConfirm} "${name}"?`)) {
      await onDeleteNotebook(notebook.id);
      setIsDropdownOpen(false);
    }
  }

  function selectNotebook(notebookId) {
    onSelectNotebook(notebookId);
    setIsDropdownOpen(false);
  }

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
          <h2 className="font-bold">Notebook</h2>
      </div>

      <div className="relative mt-4">
        <button
          type="button"
          className="flex w-full items-center justify-between gap-3 rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-left text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
          onClick={() => setIsDropdownOpen((current) => !current)}
          aria-haspopup="listbox"
          aria-expanded={isDropdownOpen}
        >
          <span className="min-w-0 truncate font-medium">
            {selectedNotebook?.title || text.untitledNotebook}
          </span>
          <ChevronDown
            className={`shrink-0 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
            size={17}
          />
        </button>

        {isDropdownOpen && (
          <div
            className="absolute left-0 right-0 z-20 mt-2 max-h-64 overflow-y-auto rounded-lg border border-zinc-200 bg-white p-1 shadow-sm"
            role="listbox"
          >
            {notebooks.map((notebook) => {
              const name = notebook.title || text.untitledNotebook;
              const isSelected = notebook.id === selectedNotebookId;

              return (
                <div
                  key={notebook.id}
                  className={`flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-zinc-50 ${
                    isSelected ? 'bg-teal-50 text-teal-900' : 'text-zinc-700'
                  }`}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => selectNotebook(notebook.id)}
                >
                  <span className="min-w-0 flex-1 truncate font-medium">{name}</span>
                  <button
                    type="button"
                    className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-rose-600 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-40"
                    onClick={(event) => confirmDeleteNotebook(event, notebook)}
                    disabled={isNotebookLoading}
                    aria-label={`${text.deleteNotebook}: ${name}`}
                    title={text.deleteNotebook}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
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
  reloadNotebooks: 'Reload notebooks',
  deleteNotebook: 'Delete notebook',
  deleteNotebookConfirm: 'Delete notebook',
  untitledNotebook: 'Untitled notebook',
  newNotebook: 'New notebook',
};
