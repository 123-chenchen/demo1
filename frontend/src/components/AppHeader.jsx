import React from 'react';
import { BarChart3, FileText, History, LogOut, MessageSquareText, MessageSquare, Settings, User } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import { API_ENDPOINT_LABEL } from '../api.js';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: MessageSquareText },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/history', label: 'History', icon: History },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/profile', label: 'Profile', icon: User },
];

export function AppHeader({ user, isAuthDisabled, onLogout }) {
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 lg:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-600 text-white">
              <MessageSquareText size={22} />
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight sm:text-xl">PDF Chatbot</h1>
              <p className="text-sm text-zinc-500">Upload PDFs and ask questions based on extracted content</p>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-600">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Backend {API_ENDPOINT_LABEL}
            </div>

            {isAuthDisabled ? (
              <div className="inline-flex items-center justify-center rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">
                Sign-in disabled
              </div>
            ) : (
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-semibold text-zinc-700 hover:bg-zinc-50"
                onClick={onLogout}
              >
                <LogOut size={16} />
                Sign out {user?.name || user?.email}
              </button>
            )}
          </div>
        </div>

        <nav className="flex gap-2 overflow-x-auto pb-1">
          {navItems.map(({ to, label, icon: Icon }) => (
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
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
