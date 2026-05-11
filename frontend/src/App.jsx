import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  FileText,
  Loader2,
  MessageSquareText,
  RefreshCw,
  Search,
  Send,
  UploadCloud,
  User,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const initialMessages = [
  {
    id: 'welcome',
    role: 'assistant',
    content: 'Upload một file PDF đã xử lý, chọn tài liệu, rồi hỏi nội dung trong tài liệu đó.',
    sources: [],
  },
];

function formatBytes(value) {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatStatus(status) {
  const labels = {
    pending: 'Đang chờ',
    processing: 'Đang xử lý',
    processed: 'Sẵn sàng',
    failed: 'Lỗi',
  };
  return labels[status] || status || 'Không rõ';
}

function statusClass(status) {
  if (status === 'processed') return 'bg-emerald-50 text-emerald-700 ring-emerald-100';
  if (status === 'failed') return 'bg-rose-50 text-rose-700 ring-rose-100';
  return 'bg-amber-50 text-amber-700 ring-amber-100';
}

async function parseResponse(response) {
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed with status ${response.status}`);
  }
  return data;
}

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [messages, setMessages] = useState(initialMessages);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState('');
  const [lastAnswer, setLastAnswer] = useState(null);
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  const selectedDocument = documents.find((item) => item.id === selectedDocumentId) || null;
  const filteredDocuments = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) return documents;
    return documents.filter((item) => item.original_file_name.toLowerCase().includes(normalized));
  }, [documents, search]);

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAsking]);

  async function loadDocuments() {
    setIsLoadingDocuments(true);
    setError('');
    try {
      const data = await fetch(`${API_BASE_URL}/api/documents/`).then(parseResponse);
      setDocuments(data);
      setSelectedDocumentId((current) => current || data.find((item) => item.status === 'processed')?.id || data[0]?.id || '');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  async function uploadPdf(file) {
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Chỉ hỗ trợ file PDF.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    setIsUploading(true);
    setError('');
    try {
      const uploaded = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      }).then(parseResponse);
      setDocuments((current) => [uploaded, ...current.filter((item) => item.id !== uploaded.id)]);
      setSelectedDocumentId(uploaded.id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Đã upload và xử lý "${uploaded.original_file_name}". Bạn có thể hỏi tài liệu này ngay.`,
          sources: [],
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function askQuestion(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isAsking) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
      sources: [],
    };
    setMessages((current) => [...current, userMessage]);
    setQuery('');
    setIsAsking(true);
    setError('');

    try {
      const answer = await fetch(`${API_BASE_URL}/api/chatbot/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: trimmed,
          document_id: selectedDocument?.status === 'processed' ? selectedDocument.id : null,
          top_k: 5,
          save_history: false,
        }),
      }).then(parseResponse);

      setLastAnswer(answer);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: answer.answer,
          sources: answer.sources || [],
        },
      ]);
    } catch (err) {
      setError(err.message);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Không trả lời được câu hỏi: ${err.message}`,
          sources: [],
          isError: true,
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-100 text-zinc-950">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 lg:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-600 text-white">
              <MessageSquareText size={22} />
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight sm:text-xl">PDF Chatbot</h1>
              <p className="text-sm text-zinc-500">Upload PDF, hỏi đáp theo nội dung đã trích xuất</p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-600 sm:flex">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            Backend {API_BASE_URL.replace(/^https?:\/\//, '')}
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[320px_minmax(0,1fr)_320px] lg:px-6">
        <aside className="space-y-4">
          <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="font-bold">Tài liệu PDF</h2>
                <p className="text-sm text-zinc-500">{documents.length} file trong hệ thống</p>
              </div>
              <button
                className="rounded-lg border border-zinc-200 p-2 text-zinc-600 hover:bg-zinc-50"
                onClick={loadDocuments}
                disabled={isLoadingDocuments}
                aria-label="Tải lại tài liệu"
              >
                <RefreshCw size={18} className={isLoadingDocuments ? 'animate-spin' : ''} />
              </button>
            </div>

            <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-teal-300 bg-teal-50 px-4 py-6 text-center hover:bg-teal-100">
              {isUploading ? <Loader2 className="animate-spin text-teal-700" size={26} /> : <UploadCloud className="text-teal-700" size={28} />}
              <span className="mt-2 text-sm font-semibold text-teal-900">{isUploading ? 'Đang upload và xử lý...' : 'Chọn PDF để upload'}</span>
              <span className="mt-1 text-xs text-teal-700">Backend sẽ lưu, trích text, chunk và index vector</span>
              <input
                ref={fileInputRef}
                className="hidden"
                type="file"
                accept="application/pdf,.pdf"
                disabled={isUploading}
                onChange={(event) => uploadPdf(event.target.files?.[0])}
              />
            </label>

            <div className="relative mt-4">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={17} />
              <input
                className="w-full rounded-lg border border-zinc-200 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tìm file..."
              />
            </div>
          </section>

          <section className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
            {filteredDocuments.map((document) => (
              <button
                key={document.id}
                className={`w-full rounded-lg border p-3 text-left shadow-sm transition ${
                  selectedDocumentId === document.id ? 'border-teal-500 bg-white ring-4 ring-teal-100' : 'border-zinc-200 bg-white hover:border-zinc-300'
                }`}
                onClick={() => setSelectedDocumentId(document.id)}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 rounded-lg bg-zinc-100 p-2 text-zinc-700">
                    <FileText size={18} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{document.original_file_name}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {document.total_pages || 0} trang · {document.total_chunks || 0} chunks · {formatBytes(document.file_size_bytes)}
                    </p>
                    <span className={`mt-2 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${statusClass(document.status)}`}>
                      {formatStatus(document.status)}
                    </span>
                  </div>
                </div>
              </button>
            ))}
            {!isLoadingDocuments && filteredDocuments.length === 0 && (
              <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-500">Chưa có PDF nào. Upload một file để bắt đầu.</div>
            )}
          </section>
        </aside>

        <section className="flex min-h-[680px] flex-col rounded-lg border border-zinc-200 bg-white shadow-sm">
          <div className="border-b border-zinc-200 px-4 py-3">
            <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-zinc-500">Đang hỏi</p>
                <h2 className="truncate text-lg font-bold">{selectedDocument?.original_file_name || 'Toàn bộ tài liệu public'}</h2>
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
              <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.role === 'assistant' && (
                  <div className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${message.isError ? 'bg-rose-100 text-rose-700' : 'bg-teal-100 text-teal-700'}`}>
                    <Bot size={18} />
                  </div>
                )}
                <div className={`max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'bg-zinc-950 text-white' : message.isError ? 'bg-rose-50 text-rose-900' : 'bg-zinc-100 text-zinc-900'}`}>
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.sources?.length > 0 && (
                    <p className="mt-2 text-xs font-semibold text-zinc-500">{message.sources.length} nguồn liên quan</p>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white">
                    <User size={17} />
                  </div>
                )}
              </div>
            ))}
            {isAsking && (
              <div className="flex gap-3">
                <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 text-teal-700">
                  <Bot size={18} />
                </div>
                <div className="rounded-lg bg-zinc-100 px-4 py-3 text-sm text-zinc-600">
                  <Loader2 className="inline animate-spin" size={16} /> Đang truy xuất đoạn liên quan và tạo câu trả lời...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form className="border-t border-zinc-200 p-4" onSubmit={askQuestion}>
            <div className="flex gap-2">
              <input
                className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-3 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ví dụ: Tóm tắt tài liệu này trong 5 ý chính..."
                disabled={isAsking}
              />
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-3 text-sm font-bold text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                disabled={!query.trim() || isAsking}
              >
                {isAsking ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                <span className="hidden sm:inline">Gửi</span>
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-4">
          <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="text-emerald-600" size={19} />
              <h2 className="font-bold">Trạng thái</h2>
            </div>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Tài liệu chọn</dt>
                <dd className="text-right font-semibold">{selectedDocument ? formatStatus(selectedDocument.status) : 'Chưa chọn'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Nguồn truy xuất</dt>
                <dd className="text-right font-semibold">{lastAnswer?.retriever || 'Chưa hỏi'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Model trả lời</dt>
                <dd className="text-right font-semibold">{lastAnswer?.generator_model_name || lastAnswer?.generator_provider || 'Chưa hỏi'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Độ trễ</dt>
                <dd className="text-right font-semibold">{lastAnswer ? `${Math.round(lastAnswer.total_latency_ms)} ms` : 'N/A'}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
            <h2 className="font-bold">Nguồn trích dẫn</h2>
            <div className="mt-3 max-h-[560px] space-y-3 overflow-y-auto pr-1">
              {(lastAnswer?.sources || []).map((source, index) => (
                <article key={`${source.chunk_id}-${index}`} className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-semibold">{source.original_file_name}</p>
                    <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-zinc-600 ring-1 ring-zinc-200">
                      #{index + 1}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    Trang {source.page_from || '?'}{source.page_to && source.page_to !== source.page_from ? `-${source.page_to}` : ''} · chunk {source.chunk_index}
                  </p>
                  <p className="mt-2 line-clamp-5 text-sm leading-6 text-zinc-700">{source.content}</p>
                </article>
              ))}
              {!lastAnswer?.sources?.length && (
                <p className="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-500">Nguồn liên quan sẽ hiện sau khi chatbot trả lời.</p>
              )}
            </div>
          </section>
        </aside>
      </main>
    </div>
  );
}

export default App;
