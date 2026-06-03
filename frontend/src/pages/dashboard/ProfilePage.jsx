import React from 'react';

import { useAppContext } from '../../app/AppContext.jsx';

export function ProfilePage() {
  const { header } = useAppContext();
  const user = header.user;

  return (
    <main className="mx-auto max-w-3xl px-4 py-4 lg:px-6">
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Profile</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <ProfileRow label="Email" value={user?.email || 'Unknown'} />
          <ProfileRow label="Name" value={user?.name || 'Not set'} />
          <ProfileRow label="Mode" value={header.isAuthDisabled ? 'Guest access' : 'Authenticated user'} />
        </dl>
      </section>
    </main>
  );
}

function ProfileRow({ label, value }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="font-semibold text-zinc-900">{value}</dd>
    </div>
  );
}
