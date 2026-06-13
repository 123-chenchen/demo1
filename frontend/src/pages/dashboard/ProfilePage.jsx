import React from 'react';

import { useAppContext } from '../../app/AppContext.jsx';

export function ProfilePage() {
  const { header } = useAppContext();
  const user = header.user;
  const displayName = resolveUserDisplayName(user);

  return (
    <main className="mx-auto max-w-3xl px-4 py-4 lg:px-6">
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Profile</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <ProfileRow label="Email" value={user?.email || 'Unknown'} />
          <ProfileRow label="Name" value={displayName || 'Not set'} />
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

function resolveUserDisplayName(user) {
  const profileName = user?.profile?.name || user?.google_profile?.name || user?.googleProfile?.name;
  const value = user?.name || user?.full_name || profileName || emailPrefix(user?.email);
  return typeof value === 'string' ? value.trim() : '';
}

function emailPrefix(email) {
  if (!email) return '';
  return email.split('@')[0].split('+')[0].replace(/[._-]+/g, ' ').trim();
}
