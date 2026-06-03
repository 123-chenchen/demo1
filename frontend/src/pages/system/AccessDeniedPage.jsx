import React from 'react';
import { Link } from 'react-router-dom';

export function AccessDeniedPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-10 lg:px-6">
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Access denied</h2>
        <p className="mt-3 text-sm text-zinc-600">Your account does not have permission to open this admin route.</p>
        <Link className="mt-4 inline-flex rounded-lg bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700" to="/dashboard">
          Back to dashboard
        </Link>
      </section>
    </main>
  );
}
