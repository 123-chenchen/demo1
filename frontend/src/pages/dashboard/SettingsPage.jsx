import React from 'react';

import { API_ENDPOINT_LABEL } from '../../api.js';

export function SettingsPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-4 lg:px-6">
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Settings</h2>
        <p className="mt-3 text-sm text-zinc-600">Backend endpoint: {API_ENDPOINT_LABEL}</p>
      </section>
    </main>
  );
}
