import React, { useEffect, useMemo, useRef, useState } from 'react';

const DEFAULT_LAYOUT = {
  sourceWidth: 280,
  studioWidth: 340,
};

const SOURCE_MIN = 260;
const SOURCE_MAX = 420;
const CHAT_MIN = 420;
const STUDIO_MIN = 320;
const STUDIO_MAX = 600;
const DIVIDER_WIDTH = 10;

export function ResizableNotebookLayout({ storageKey, sources, chat, studio }) {
  const containerRef = useRef(null);
  const [layout, setLayout] = useState(() => readStoredLayout(storageKey));
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    setLayout(readStoredLayout(storageKey));
  }, [storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(layout));
  }, [layout, storageKey]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const updateWidth = () => setContainerWidth(container.clientWidth);
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const isCompact = containerWidth > 0 && containerWidth < SOURCE_MIN + STUDIO_MIN + CHAT_MIN + DIVIDER_WIDTH * 2;
  const gridTemplateColumns = useMemo(
    () => (
      isCompact
        ? `0px 0px minmax(0, 1fr) 0px 0px`
        : `${layout.sourceWidth}px ${DIVIDER_WIDTH}px minmax(${CHAT_MIN}px, 1fr) ${DIVIDER_WIDTH}px ${layout.studioWidth}px`
    ),
    [isCompact, layout.sourceWidth, layout.studioWidth],
  );

  function resetLayout() {
    setLayout(DEFAULT_LAYOUT);
  }

  function startDrag(kind, event) {
    event.preventDefault();
    const container = containerRef.current;
    if (!container) return;

    const bounds = container.getBoundingClientRect();
    const startLayout = layout;

    function handlePointerMove(pointerEvent) {
      const totalWidth = bounds.width;
      const reserved = DIVIDER_WIDTH * 2;

      if (kind === 'source') {
        const requestedSourceWidth = pointerEvent.clientX - bounds.left;
        const maxSourceWidth = Math.min(SOURCE_MAX, totalWidth - startLayout.studioWidth - CHAT_MIN - reserved);
        setLayout((current) => ({
          ...current,
          sourceWidth: clamp(requestedSourceWidth, SOURCE_MIN, Math.max(SOURCE_MIN, maxSourceWidth)),
        }));
        return;
      }

      const requestedStudioWidth = bounds.right - pointerEvent.clientX;
      const maxStudioWidth = Math.min(STUDIO_MAX, totalWidth - startLayout.sourceWidth - CHAT_MIN - reserved);
      setLayout((current) => ({
        ...current,
        studioWidth: clamp(requestedStudioWidth, STUDIO_MIN, Math.max(STUDIO_MIN, maxStudioWidth)),
      }));
    }

    function stopDrag() {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', stopDrag);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', stopDrag, { once: true });
  }

  return (
    <main
      ref={containerRef}
      className="grid h-full min-h-0 w-full overflow-hidden px-4 py-4 lg:px-6"
      style={{ gridTemplateColumns }}
    >
      <section className={`min-h-0 overflow-y-auto overflow-x-hidden ${isCompact ? 'invisible' : ''}`}>{sources}</section>
      <ColumnDivider hidden={isCompact} label="Resize sources" onPointerDown={(event) => startDrag('source', event)} onDoubleClick={resetLayout} />
      <section className="min-h-0 overflow-hidden">{chat}</section>
      <ColumnDivider hidden={isCompact} label="Resize studio" onPointerDown={(event) => startDrag('studio', event)} onDoubleClick={resetLayout} />
      <section className={`min-h-0 overflow-hidden ${isCompact ? 'invisible' : ''}`}>{studio}</section>
    </main>
  );
}

function ColumnDivider({ hidden, label, onPointerDown, onDoubleClick }) {
  if (hidden) return <span aria-hidden="true" />;

  return (
    <button
      type="button"
      className="group flex h-full cursor-col-resize items-center justify-center"
      aria-label={label}
      title={`${label}. Double click to reset.`}
      onPointerDown={onPointerDown}
      onDoubleClick={onDoubleClick}
    >
      <span className="h-full w-px rounded-full bg-zinc-200 transition group-hover:w-1 group-hover:bg-teal-400" />
    </button>
  );
}

function readStoredLayout(storageKey) {
  try {
    const raw = localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : null;
    return {
      sourceWidth: clamp(Number(parsed?.sourceWidth) || DEFAULT_LAYOUT.sourceWidth, SOURCE_MIN, SOURCE_MAX),
      studioWidth: clamp(Number(parsed?.studioWidth) || DEFAULT_LAYOUT.studioWidth, STUDIO_MIN, STUDIO_MAX),
    };
  } catch {
    return DEFAULT_LAYOUT;
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}
