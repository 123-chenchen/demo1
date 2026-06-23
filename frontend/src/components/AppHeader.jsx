import React from 'react';
import { FileText, History, MessageSquareText, Settings } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/dashboard', key: 'dashboard', icon: MessageSquareText },
  { to: '/documents', key: 'documents', icon: FileText },
  { to: '/history', key: 'history', icon: History },
];

export function AppHeader({ isAuthDisabled, language = 'en' }) {
  const text = language === 'vi' ? viText : enText;

  return (
    <header className="shrink-0 border-b border-zinc-200 bg-white">
      <div className="flex w-full flex-col gap-4 px-4 py-4 lg:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-600 text-white">
              <MessageSquareText size={22} />
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight sm:text-xl">PDF Chatbot</h1>
              <p className="text-sm text-zinc-500">{text.tagline}</p>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            {isAuthDisabled ? (
              <div className="inline-flex items-center justify-center rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">
                {text.signInDisabled}
              </div>
            ) : null}
            <NavLink
              to="/settings"
              className={({ isActive }) =>
                `inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  isActive ? 'bg-zinc-950 text-white' : 'border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50'
                }`
              }
              title={text.nav.settings}
            >
              <Settings size={16} />
              {text.nav.settings}
            </NavLink>
          </div>
        </div>

        <nav className="flex gap-2 overflow-x-auto pb-1">
          {navItems.map(({ to, key, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  isActive ? 'bg-zinc-950 text-white' : 'border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50'
                }`
              }
            >
              <Icon size={16} />
              {text.nav[key]}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}

const enText = {
  
  signInDisabled: 'Sign-in disabled',
  nav: {
    dashboard: 'Chat',
    documents: 'Documents',
    history: 'History',
    settings: 'Settings',
  },
};

const viText = {
  
  signInDisabled: 'Đăng nhập đang tắt',
  nav: {
    dashboard: 'Chat',
    documents: 'Tài liệu',
    history: 'Lịch sử',
    settings: 'Cài đặt',
  },
};
