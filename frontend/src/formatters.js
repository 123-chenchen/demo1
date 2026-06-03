export function formatBytes(value) {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function formatStatus(status) {
  const labels = {
    pending: 'Pending',
    processing: 'Processing',
    processed: 'Ready',
    failed: 'Failed',
  };
  return labels[status] || status || 'Unknown';
}

export function statusClass(status) {
  if (status === 'processed') return 'bg-emerald-50 text-emerald-700 ring-emerald-100';
  if (status === 'failed') return 'bg-rose-50 text-rose-700 ring-rose-100';
  return 'bg-amber-50 text-amber-700 ring-amber-100';
}
