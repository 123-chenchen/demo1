import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';

const adminLinks = [
  { to: '/admin', label: 'Overview', end: true },
  { to: '/admin/users/current', label: 'Users' },
];

export function AdminLayout() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-4 lg:px-6">
      <div className="mb-4 flex flex-col gap-3 border-b border-zinc-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold">Admin</h2>
          <p className="text-sm text-zinc-500">System administration routes are grouped under /admin.</p>
        </div>
        <nav className="flex flex-wrap gap-2">
          {adminLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  isActive ? 'bg-zinc-950 text-white' : 'border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <Outlet />
    </main>
  );
}
