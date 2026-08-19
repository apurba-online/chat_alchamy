import type { QueryResponse } from '../types';

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function queryLive(question: string, conversation: Array<{role: string; content: string}> = [], userEvidence: unknown[] = []): Promise<QueryResponse> {
  return postJSON<QueryResponse>('/api/query', { question, conversation, user_evidence: userEvidence, max_results: 20 });
}

export async function chat(messages: Array<{role: string; content: string}>, uploadedContext?: string): Promise<QueryResponse> {
  return postJSON<QueryResponse>('/api/chat', { messages, uploaded_context: uploadedContext || null });
}

export async function generateTitle(text: string): Promise<string> {
  const result = await postJSON<{title: string}>('/api/title', { text });
  return result.title;
}

export async function extractBiomedical(text: string, filename?: string) {
  return postJSON<{summary: string; genes: string[]; suggested_diseases: string[]}>('/api/biomedical/extract', { text, filename });
}

export async function analyzeBiomedical(input: {genes?: string[]; query?: string | null; suggestedDiseases?: string[]; paperSummary?: string | null}) {
  return postJSON<any>('/api/biomedical/analyze', {
    genes: input.genes || [],
    query: input.query || null,
    suggested_diseases: input.suggestedDiseases || [],
    paper_summary: input.paperSummary || null,
  });
}
