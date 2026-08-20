import type { QueryResponse, SystemHealth, TableData } from '../types';

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const DEFAULT_TIMEOUT_MS = 55_000;

async function errorText(response: Response): Promise<string> {
  const fallback = `Request failed with HTTP ${response.status}`;
  let text = '';
  try {
    text = await response.text();
  } catch {
    return fallback;
  }
  if (!text.trim()) return fallback;
  try {
    const data = JSON.parse(text);
    return data?.detail || data?.message || text;
  } catch {
    return text;
  }
}

async function request(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_URL}${path}`, {
      ...init,
      cache: 'no-store',
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('The request timed out before the evidence workflow completed. Please try a narrower query.');
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const response = await request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json() as Promise<T>;
}

export async function getSystemHealth(): Promise<SystemHealth> {
  const response = await request('/api/health', {}, 12_000);
  if (!response.ok) throw new Error(await errorText(response));
  return response.json() as Promise<SystemHealth>;
}

export async function queryLive(
  question: string,
  conversation: Array<{ role: string; content: string }> = [],
  userEvidence: unknown[] = [],
): Promise<QueryResponse> {
  return postJSON<QueryResponse>('/api/query', {
    question,
    conversation,
    user_evidence: userEvidence,
    max_results: 20,
  });
}

export async function chat(
  messages: Array<{ role: string; content: string }>,
  uploadedContext?: string,
): Promise<QueryResponse> {
  return postJSON<QueryResponse>('/api/chat', {
    messages,
    uploaded_context: uploadedContext || null,
  });
}

export async function generateTitle(text: string): Promise<string> {
  const result = await postJSON<{ title: string }>('/api/title', { text });
  return result.title;
}

export async function extractBiomedical(text: string, filename?: string) {
  return postJSON<{ summary: string; genes: string[]; suggested_diseases: string[] }>(
    '/api/biomedical/extract',
    { text, filename },
  );
}

export async function uploadBiomedicalDocument(file: File) {
  const form = new FormData();
  form.append('file', file);
  const response = await request('/api/biomedical/upload', { method: 'POST', body: form });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json() as Promise<{ summary: string; genes: string[]; suggested_diseases: string[] }>;
}

export async function analyzeBiomedical(input: {
  genes?: string[];
  query?: string | null;
  suggestedDiseases?: string[];
  paperSummary?: string | null;
}) {
  return postJSON<any>('/api/biomedical/analyze', {
    genes: input.genes || [],
    query: input.query || null,
    suggested_diseases: input.suggestedDiseases || [],
    paper_summary: input.paperSummary || null,
  });
}

export async function parseSpreadsheet(file: File): Promise<{ filename: string; rows: Record<string, unknown>[] }> {
  const form = new FormData();
  form.append('file', file);
  const response = await request('/api/data/parse', { method: 'POST', body: form });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json() as Promise<{ filename: string; rows: Record<string, unknown>[] }>;
}

export async function exportTableXlsx(table: TableData): Promise<Blob> {
  const response = await request('/api/data/export_xlsx', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(table),
  });
  if (!response.ok) throw new Error(await errorText(response));
  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
