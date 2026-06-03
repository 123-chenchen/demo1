import React from 'react';
import { useParams } from 'react-router-dom';

export function AdminUserPage() {
  const { userId } = useParams();

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
      <h2 className="text-xl font-bold">User Detail</h2>
      <p className="mt-3 text-sm text-zinc-600">
        User route id: <span className="font-semibold text-zinc-950">{userId}</span>
      </p>
    </section>
  );
}
