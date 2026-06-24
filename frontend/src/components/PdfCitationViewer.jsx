import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { FileText, Loader2, Maximize2, ZoomIn, ZoomOut } from "lucide-react";
import * as pdfjsLib from "pdfjs-dist";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import { ACCESS_TOKEN_KEY, apiFetchBlob } from "../api.js";
import {
  displayDocumentTitle,
  displayOriginalFileName,
} from "../documentTitles.js";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

const pdfDocumentCache = new Map();
const objectUrlCache = new Map();

export function PdfCitationViewer({
  document,
  documents = [],
  activeCitation,
}) {
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [zoom, setZoom] = useState(1);
  const viewerDocuments = useMemo(
    () =>
      uniqueDocuments(
        documents.length ? documents : document ? [document] : [],
      ),
    [documents, document],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const updateWidth = () => setContainerWidth(container.clientWidth);
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setZoom(1);
  }, [viewerDocuments.map((item) => item.id).join("|")]);

  const headerTitle =
    viewerDocuments.length > 1
      ? `${viewerDocuments.length} PDFs selected`
      : viewerDocuments[0]
        ? displayDocumentTitle(viewerDocuments[0])
        : "PDF viewer";

  return (
    <section className="flex h-full min-h-0 flex-col rounded-lg border border-zinc-200 bg-white shadow-sm">
      <div className="flex flex-row items-center justify-between gap-3 border-b border-zinc-200 px-4 py-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-bold text-zinc-950">
            {headerTitle}
          </h3>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <IconButton label="Fit width" onClick={() => setZoom(1)}>
            <Maximize2 size={16} />
          </IconButton>

          <IconButton
            label="Zoom out"
            onClick={() =>
              setZoom((current) =>
                Math.max(0.65, Number((current - 0.15).toFixed(2))),
              )
            }
          >
            <ZoomOut size={16} />
          </IconButton>

          <span className="w-12 text-center text-xs font-semibold text-zinc-600">
            {Math.round(zoom * 100)}%
          </span>

          <IconButton
            label="Zoom in"
            onClick={() =>
              setZoom((current) =>
                Math.min(2.25, Number((current + 0.15).toFixed(2))),
              )
            }
          >
            <ZoomIn size={16} />
          </IconButton>
        </div>
      </div>

      <div
        ref={containerRef}
        data-pdf-scroll-container
        className="relative min-h-0 flex-1 overflow-auto bg-zinc-100 p-4"
      >
        {!viewerDocuments.length && (
          <div className="flex h-full min-h-[360px] items-center justify-center text-center">
            <div className="max-w-xs">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-white text-zinc-700 shadow-sm">
                <FileText size={22} />
              </div>
              <h3 className="mt-4 text-base font-bold text-zinc-950">
                Studio preview
              </h3>

            </div>
          </div>
        )}

        {viewerDocuments.map((item) => (
          <PdfDocumentPreview
            key={item.id}
            document={item}
            activeCitation={activeCitation}
            containerRef={containerRef}
            containerWidth={containerWidth}
            zoom={zoom}
          />
        ))}
      </div>
    </section>
  );
}

function PdfDocumentPreview({
  document,
  activeCitation,
  containerRef,
  containerWidth,
  zoom,
}) {
  const sectionRef = useRef(null);
  const [pdfDocument, setPdfDocument] = useState(null);
  const [pageCount, setPageCount] = useState(0);
  const [pageSizes, setPageSizes] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError("");
    setPageSizes({});
    setCurrentPage(1);

    loadPdfDocument(document.id)
      .then((loadedPdf) => {
        if (cancelled) return;
        setPdfDocument(loadedPdf);
        setPageCount(loadedPdf.numPages);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setPdfDocument(null);
          setPageCount(0);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [document.id]);

  useEffect(() => {
    const container = containerRef.current;
    const section = sectionRef.current;
    if (!container || !section) return undefined;

    const updateCurrentPage = () => {
      const pages = Array.from(section.querySelectorAll("[data-page-number]"));
      const containerTop = container.getBoundingClientRect().top;
      const marker =
        container.scrollTop + Math.max(120, container.clientHeight * 0.2);
      const activePage = pages.reduce((current, page) => {
        const pageNumber = Number(
          page.getAttribute("data-page-number") || current,
        );
        const pageTop =
          container.scrollTop + page.getBoundingClientRect().top - containerTop;
        return pageTop <= marker ? pageNumber : current;
      }, 1);
      setCurrentPage(activePage);
    };

    updateCurrentPage();
    container.addEventListener("scroll", updateCurrentPage, { passive: true });
    return () => container.removeEventListener("scroll", updateCurrentPage);
  }, [containerRef, pageCount]);

  useEffect(() => {
    if (
      activeCitation?.document_id &&
      String(activeCitation.document_id) !== String(document.id)
    )
      return;
    requestAnimationFrame(() =>
      scrollToActiveCitation(
        containerRef.current,
        sectionRef.current,
        activeCitation,
        pageSizes,
      ),
    );
  }, [activeCitation, containerRef, document.id, pageSizes]);

  const registerPageSize = useCallback((pageNumber, nextSize) => {
    setPageSizes((current) => {
      const previous = current[pageNumber];
      if (
        previous &&
        Math.round(previous.width) === Math.round(nextSize.width) &&
        Math.round(previous.height) === Math.round(nextSize.height)
      ) {
        return current;
      }
      return { ...current, [pageNumber]: nextSize };
    });
  }, []);

  const pageNumbers = useMemo(
    () => Array.from({ length: pageCount }, (_, index) => index + 1),
    [pageCount],
  );

  return (
    <article
      ref={sectionRef}
      className="mb-5 rounded-lg border border-zinc-200 bg-white shadow-sm last:mb-0"
    >

      <div className="relative p-3">
        {error && (
          <div className="mb-3 flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
            <FileText className="mt-0.5 shrink-0" size={18} />
            <span>{error}</span>
          </div>
        )}
        {pdfDocument &&
          pageNumbers.map((pageNumber) => (
            <PdfPage
              key={`${document.id}-${pageNumber}`}
              pdfDocument={pdfDocument}
              pageNumber={pageNumber}
              containerWidth={containerWidth}
              zoom={zoom}
              onPageSize={registerPageSize}
            />
          ))}
        {isLoading && (
          <div className="absolute left-3 top-3 inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-semibold text-zinc-600 shadow-sm">
            <Loader2 className="animate-spin" size={16} />
            Loading PDF...
          </div>
        )}
      </div>
    </article>
  );
}

function PdfPage({
  pdfDocument,
  pageNumber,
  containerWidth,
  zoom,
  onPageSize,
}) {
  const canvasRef = useRef(null);
  const renderTaskRef = useRef(null);
  const [pageSize, setPageSize] = useState({
    width: 0,
    height: 0,
    baseWidth: 0,
    baseHeight: 0,
  });
  const [error, setError] = useState("");

  useEffect(() => {
    if (!pdfDocument || !canvasRef.current || !containerWidth) return undefined;

    let cancelled = false;
    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");

    if (renderTaskRef.current) {
      renderTaskRef.current.cancel();
      renderTaskRef.current = null;
    }

    pdfDocument
      .getPage(pageNumber)
      .then((page) => {
        if (cancelled) return null;
        const baseViewport = page.getViewport({ scale: 1 });
        const availableWidth = Math.max(280, containerWidth - 32);
        const scale = Math.max(
          0.35,
          (availableWidth / baseViewport.width) * zoom,
        );
        const viewport = page.getViewport({ scale });
        const outputScale = window.devicePixelRatio || 1;

        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;
        context.setTransform(outputScale, 0, 0, outputScale, 0, 0);

        const nextSize = {
          width: viewport.width,
          height: viewport.height,
          baseWidth: baseViewport.width,
          baseHeight: baseViewport.height,
        };
        setPageSize(nextSize);
        onPageSize(pageNumber, nextSize);

        const renderTask = page.render({ canvasContext: context, viewport });
        renderTaskRef.current = renderTask;
        return renderTask.promise;
      })
      .then(() => {
        if (!cancelled) setError("");
      })
      .catch((err) => {
        if (!cancelled && err?.name !== "RenderingCancelledException") {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          renderTaskRef.current = null;
        }
      });

    return () => {
      cancelled = true;
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
        renderTaskRef.current = null;
      }
    };
  }, [pdfDocument, pageNumber, containerWidth, zoom, onPageSize]);

  return (
    <div
      data-page-number={pageNumber}
      className="relative mx-auto mb-4 w-fit bg-white shadow-sm"
    >
      <canvas ref={canvasRef} className="block" />
      <span className="absolute bottom-2 right-2 rounded bg-zinc-950/70 px-2 py-1 text-xs font-semibold text-white">
        {pageNumber}
      </span>
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/90 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}
    </div>
  );
}

async function loadPdfDocument(documentId) {
  if (pdfDocumentCache.has(documentId)) {
    return pdfDocumentCache.get(documentId);
  }

  let objectUrl = objectUrlCache.get(documentId);
  if (!objectUrl) {
    const blob = await apiFetchBlob(
      `/api/documents/${documentId}/pdf`,
      {},
      localStorage.getItem(ACCESS_TOKEN_KEY) || "",
    );
    objectUrl = URL.createObjectURL(blob);
    objectUrlCache.set(documentId, objectUrl);
  }

  const loadingTask = pdfjsLib.getDocument({ url: objectUrl });
  const pdf = await loadingTask.promise;
  pdfDocumentCache.set(documentId, pdf);
  return pdf;
}

function IconButton({ label, disabled, onClick, children }) {
  return (
    <button
      type="button"
      className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-700 hover:border-teal-300 hover:text-teal-800 disabled:cursor-not-allowed disabled:opacity-40"
      disabled={disabled}
      onClick={onClick}
      aria-label={label}
      title={label}
    >
      {children}
    </button>
  );
}

function scrollToActiveCitation(container, section, citation, pageSizes) {
  const pageNumber = citationPageNumber(citation);
  if (!container || !section || !pageNumber) return;

  const pageElement = section.querySelector(
    `[data-page-number="${pageNumber}"]`,
  );
  if (!pageElement) return;

  const containerTop = container.getBoundingClientRect().top;
  const pageTop =
    container.scrollTop +
    pageElement.getBoundingClientRect().top -
    containerTop;
  const pageSize = pageSizes[pageNumber];
  if (!citation?.bbox || !pageSize?.height) {
    container.scrollTo({ top: Math.max(0, pageTop - 16), behavior: "smooth" });
    return;
  }

  const pageHeight =
    citation.page_height || pageSize.baseHeight || pageSize.height;
  const citationTop = (citation.bbox[1] / pageHeight) * pageSize.height;
  container.scrollTo({
    top: Math.max(0, pageTop + citationTop - 120),
    behavior: "smooth",
  });
}

function citationPageNumber(citation) {
  return (
    citation?.page_number || citation?.page_from || citation?.page_to || null
  );
}

function uniqueDocuments(documents) {
  const seen = new Set();
  return documents.filter((document) => {
    if (!document?.id || seen.has(document.id)) return false;
    seen.add(document.id);
    return true;
  });
}
