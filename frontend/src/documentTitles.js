const titleKeys = [
  'display_title',
  'title',
  'document_title',
  'pdf_title',
  'extracted_title',
  'subject',
  'topic',
  'summary_title',
];

export function displayDocumentTitle(documentOrSource) {
  if (!documentOrSource) return 'Selected source';

  const metadata = documentOrSource.metadata || documentOrSource.extra_metadata || {};
  for (const key of titleKeys) {
    const title = cleanTitle(metadata[key] || documentOrSource[key]);
    if (title) return title;
  }

  const sourceTitle = cleanTitle(documentOrSource.document_name);
  if (sourceTitle && !looksLikeRawPdfName(sourceTitle)) return sourceTitle;

  const originalName = documentOrSource.original_file_name || documentOrSource.file_name || documentOrSource.document_name;
  return cleanFilename(originalName) || 'Selected source';
}

export function displayDocumentListTitle(documents) {
  if (!documents?.length) return 'No sources selected';
  if (documents.length === 1) return displayDocumentTitle(documents[0]);
  return `Selected Sources (${documents.length})`;
}

function cleanTitle(value) {
  if (typeof value !== 'string') return '';
  const title = value.replace(/\0/g, ' ').replace(/\s+/g, ' ').trim();
  if (!title || title.length < 4 || title.toLowerCase() === 'untitled') return '';
  return title;
}

function cleanFilename(value) {
  if (typeof value !== 'string') return '';
  const fileName = value.replace(/\\/g, '/').split('/').pop() || '';
  const withoutExtension = fileName.replace(/\.pdf$/i, '').replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
  return withoutExtension || fileName;
}

function looksLikeRawPdfName(value) {
  return /\.pdf$/i.test(value) || /^[\d._-]+v?\d*$/i.test(value) || /^[a-f0-9-]{12,}$/i.test(value);
}
