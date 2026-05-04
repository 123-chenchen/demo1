import { useMemo, useState } from 'react';
import {
  Bell,
  CheckCircle2,
  ChevronDown,
  CreditCard,
  FileText,
  LayoutDashboard,
  Menu,
  Plus,
  Search,
  Settings,
  Users,
  X,
} from 'lucide-react';

const stats = [
  { label: 'Doanh thu', value: '248.6M', change: '+12.4%', icon: CreditCard, tone: 'text-emerald-700 bg-emerald-50' },
  { label: 'Khach hang', value: '12,840', change: '+8.2%', icon: Users, tone: 'text-blue-700 bg-blue-50' },
  { label: 'Don hang', value: '1,284', change: '+4.8%', icon: FileText, tone: 'text-amber-700 bg-amber-50' },
  { label: 'Hoan thanh', value: '96.2%', change: '+2.1%', icon: CheckCircle2, tone: 'text-teal-700 bg-teal-50' },
];

const mockRows = [
  { id: 'INV-1008', customer: 'Nguyen Minh Anh', product: 'Business Plan', amount: '18.500.000d', status: 'Paid', date: '04/05/2026' },
  { id: 'INV-1007', customer: 'Tran Hoang Nam', product: 'Team Workspace', amount: '9.200.000d', status: 'Pending', date: '03/05/2026' },
  { id: 'INV-1006', customer: 'Le Thanh Mai', product: 'Analytics Pro', amount: '12.800.000d', status: 'Paid', date: '02/05/2026' },
  { id: 'INV-1005', customer: 'Pham Quoc Huy', product: 'Automation Kit', amount: '7.400.000d', status: 'Overdue', date: '01/05/2026' },
  { id: 'INV-1004', customer: 'Do Gia Linh', product: 'Starter Suite', amount: '4.900.000d', status: 'Paid', date: '30/04/2026' },
];

const navItems = [
  { label: 'Tong quan', icon: LayoutDashboard, active: true },
  { label: 'Khach hang', icon: Users },
  { label: 'Hoa don', icon: FileText },
  { label: 'Cai dat', icon: Settings },
];

function Sidebar({ open, onClose }) {
  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-slate-950/40 transition-opacity lg:hidden ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 -translate-x-full flex-col border-r border-slate-200 bg-white px-4 py-5 transition-transform lg:static lg:translate-x-0 ${
          open ? 'translate-x-0' : ''
        }`}
      >
        <div className="flex items-center justify-between px-2">
          <div>
            <p className="text-sm font-semibold text-slate-500">Acme Cloud</p>
            <h1 className="text-xl font-bold text-slate-950">Dashboard</h1>
          </div>
          <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden" onClick={onClose} aria-label="Dong menu">
            <X size={20} />
          </button>
        </div>

        <nav className="mt-8 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.label}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                item.active ? 'bg-slate-950 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
              }`}
            >
              <item.icon size={18} />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="mt-auto rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-950">Enterprise</p>
          <p className="mt-1 text-sm text-slate-500">Su dung 72% han muc thang nay.</p>
          <div className="mt-3 h-2 rounded-full bg-slate-200">
            <div className="h-2 w-[72%] rounded-full bg-slate-950" />
          </div>
        </div>
      </aside>
    </>
  );
}

function Header({ onMenuClick, onAddClick }) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 px-4 py-4 backdrop-blur lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={onMenuClick} aria-label="Mo menu">
            <Menu size={22} />
          </button>
          <div>
            <h2 className="text-xl font-bold text-slate-950 sm:text-2xl">Tong quan kinh doanh</h2>
            <p className="text-sm text-slate-500">Cap nhat theo du lieu mau trong ngay 04/05/2026</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="hidden rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 sm:inline-flex" aria-label="Thong bao">
            <Bell size={20} />
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 sm:px-4"
            onClick={onAddClick}
          >
            <Plus size={18} />
            <span className="hidden sm:inline">Them moi</span>
          </button>
        </div>
      </div>
    </header>
  );
}

function StatCard({ item }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">{item.label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{item.value}</p>
        </div>
        <div className={`rounded-lg p-3 ${item.tone}`}>
          <item.icon size={21} />
        </div>
      </div>
      <p className="mt-4 text-sm font-semibold text-emerald-700">{item.change} so voi thang truoc</p>
    </article>
  );
}

function Filters({ query, status, onQueryChange, onStatusChange }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
        <input
          className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-4 focus:ring-slate-100"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Tim theo ma, khach hang, san pham..."
        />
      </div>
      <div className="relative md:w-48">
        <select
          className="w-full appearance-none rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-700 outline-none transition focus:border-slate-400 focus:ring-4 focus:ring-slate-100"
          value={status}
          onChange={(event) => onStatusChange(event.target.value)}
        >
          <option value="All">Tat ca trang thai</option>
          <option value="Paid">Paid</option>
          <option value="Pending">Pending</option>
          <option value="Overdue">Overdue</option>
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
      </div>
    </div>
  );
}

function DataTable({ rows }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['Ma', 'Khach hang', 'San pham', 'Gia tri', 'Trang thai', 'Ngay'].map((head) => (
                <th key={head} className="px-5 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                  {head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => (
              <tr key={row.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-5 py-4 text-sm font-semibold text-slate-950">{row.id}</td>
                <td className="whitespace-nowrap px-5 py-4 text-sm text-slate-700">{row.customer}</td>
                <td className="whitespace-nowrap px-5 py-4 text-sm text-slate-600">{row.product}</td>
                <td className="whitespace-nowrap px-5 py-4 text-sm font-semibold text-slate-950">{row.amount}</td>
                <td className="whitespace-nowrap px-5 py-4">
                  <StatusBadge status={row.status} />
                </td>
                <td className="whitespace-nowrap px-5 py-4 text-sm text-slate-500">{row.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="px-5 py-10 text-center text-sm text-slate-500">Khong co du lieu phu hop.</p>}
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    Paid: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    Pending: 'bg-amber-50 text-amber-700 ring-amber-100',
    Overdue: 'bg-rose-50 text-rose-700 ring-rose-100',
  };

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${styles[status]}`}>
      {status}
    </span>
  );
}

function AddModal({ open, onClose, onCreate }) {
  const [form, setForm] = useState({ customer: '', product: '', amount: '' });

  if (!open) return null;

  const handleSubmit = (event) => {
    event.preventDefault();
    onCreate(form);
    setForm({ customer: '', product: '', amount: '' });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/45 p-4 sm:items-center">
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-soft">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-950">Them hoa don moi</h3>
            <p className="text-sm text-slate-500">Nhap thong tin co ban de tao ban ghi mau.</p>
          </div>
          <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={onClose} aria-label="Dong modal">
            <X size={20} />
          </button>
        </div>

        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          <FormField label="Khach hang" value={form.customer} onChange={(value) => setForm({ ...form, customer: value })} placeholder="VD: Nguyen Van A" />
          <FormField label="San pham" value={form.product} onChange={(value) => setForm({ ...form, product: value })} placeholder="VD: Business Plan" />
          <FormField label="Gia tri" value={form.amount} onChange={(value) => setForm({ ...form, amount: value })} placeholder="VD: 5.000.000d" />
          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
            <button type="button" className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50" onClick={onClose}>
              Huy
            </button>
            <button type="submit" className="rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800">
              Tao moi
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function FormField({ label, value, onChange, placeholder }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-slate-700">{label}</span>
      <input
        required
        className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-slate-400 focus:ring-4 focus:ring-slate-100"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [rows, setRows] = useState(mockRows);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All');

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesStatus = status === 'All' || row.status === status;
      const matchesQuery =
        !normalizedQuery ||
        [row.id, row.customer, row.product].some((value) => value.toLowerCase().includes(normalizedQuery));
      return matchesStatus && matchesQuery;
    });
  }, [query, rows, status]);

  const handleCreate = (form) => {
    const newRow = {
      id: `INV-${1000 + rows.length + 1}`,
      customer: form.customer,
      product: form.product,
      amount: form.amount,
      status: 'Pending',
      date: '04/05/2026',
    };
    setRows((current) => [newRow, ...current]);
    setModalOpen(false);
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 lg:flex">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="min-w-0 flex-1">
        <Header onMenuClick={() => setSidebarOpen(true)} onAddClick={() => setModalOpen(true)} />
        <main className="space-y-6 px-4 py-6 lg:px-8">
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {stats.map((item) => (
              <StatCard key={item.label} item={item} />
            ))}
          </section>

          <section className="space-y-4">
            <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
              <div>
                <h3 className="text-lg font-bold text-slate-950">Hoa don gan day</h3>
                <p className="text-sm text-slate-500">Quan ly, tim kiem va loc danh sach giao dich.</p>
              </div>
              <p className="text-sm font-medium text-slate-500">{filteredRows.length} ket qua</p>
            </div>
            <Filters query={query} status={status} onQueryChange={setQuery} onStatusChange={setStatus} />
            <DataTable rows={filteredRows} />
          </section>
        </main>
      </div>
      <AddModal open={modalOpen} onClose={() => setModalOpen(false)} onCreate={handleCreate} />
    </div>
  );
}
