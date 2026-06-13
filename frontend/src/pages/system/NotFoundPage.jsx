import React from 'react';
import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-10 lg:px-6">
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Page not found</h2>
        <p className="mt-3 text-sm text-zinc-600">This route is not registered in the frontend router.</p>
        <Link className="mt-4 inline-flex rounded-lg bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700" to="/dashboard">
          Back to Chat
        </Link>
      </section>
    </main>
  );
}
