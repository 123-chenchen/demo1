export function displayDocumentTitle(documentOrSource) {
  return displayOriginalFileName(documentOrSource) || 'Selected source';
}

export function displayOriginalFileName(documentOrSource) {
  if (!documentOrSource) return '';
  const originalName = documentOrSource.original_file_name || documentOrSource.file_name || documentOrSource.document_name;
  return cleanOriginalFilename(originalName);
}

export function displayDocumentListTitle(documents) {
  if (!documents?.length) return 'No sources selected';
  if (documents.length === 1) return displayDocumentTitle(documents[0]);
  return `Selected Sources (${documents.length})`;
}

function cleanOriginalFilename(value) {
  if (typeof value !== 'string') return '';
  return value.replace(/\\/g, '/').split('/').pop()?.trim() || '';
}
