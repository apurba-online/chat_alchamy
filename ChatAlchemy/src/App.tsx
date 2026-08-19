import React, { useState } from 'react';
import { Message } from './types';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { FlaskRound as Flask, Database, Radio } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const generateMessageId = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

interface QueryResponse { answer: string; supported_claim_rate: number; warnings: string[]; evidence: Array<{ id: string; source: string; source_record_id?: string | null; source_url?: string | null; }>; }

function App() {
  const [messages, setMessages] = useState<Message[]>([{ id: 'welcome', role: 'assistant', content: 'Welcome to ChatAlchemy-Live. Ask about drug identity, DailyMed labels, FDA application records, clinical trials, or molecular targets. Answers are built from live online pharmaceutical APIs and keep record-level provenance.', timestamp: new Date() }]);
  const [isLoading, setIsLoading] = useState(false); const [error, setError] = useState<string | null>(null);
  const handleSendMessage = async (content: string) => {
    setMessages((prev) => [...prev, { id: generateMessageId(), role: 'user', content, timestamp: new Date() }]); setIsLoading(true); setError(null);
    try {
      const response = await fetch(`${API_URL}/query`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: content, max_results: 20 }) });
      if (!response.ok) { const text = await response.text(); throw new Error(text || `Backend returned HTTP ${response.status}`); }
      const data = (await response.json()) as QueryResponse; const seen = new Set<string>();
      const provenance = data.evidence.filter((item) => { const key = `${item.source}:${item.source_record_id || item.id}`; if (seen.has(key)) return false; seen.add(key); return true; }).map((item) => ({ id: item.id, source: item.source, recordId: item.source_record_id, url: item.source_url }));
      setMessages((prev) => [...prev, { id: generateMessageId(), role: 'assistant', content: data.answer, timestamp: new Date(), provenance, supportRate: data.supported_claim_rate, warnings: data.warnings }]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown request error'; setError(message);
      setMessages((prev) => [...prev, { id: generateMessageId(), role: 'assistant', content: 'I could not complete the live-source query. I will not substitute memorized pharmaceutical facts when the configured sources are unavailable.', timestamp: new Date(), warnings: [message] }]);
    } finally { setIsLoading(false); }
  };
  return <div className="flex h-screen flex-col bg-gradient-to-b from-purple-50 to-white"><header className="border-b bg-white/90 backdrop-blur-sm"><div className="mx-auto max-w-4xl p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><Flask className="h-6 w-6 text-purple-600" /><div><h1 className="text-xl font-semibold text-gray-800">ChatAlchemy-Live</h1><p className="text-xs text-gray-500">Query-time pharmaceutical evidence, no local drug database</p></div></div><div className="flex items-center gap-2 rounded-full border bg-gray-50 px-3 py-2 text-xs text-gray-600"><Radio className="h-4 w-4 text-emerald-600" /><Database className="h-4 w-4" />RxNorm · DailyMed · Drugs@FDA · ClinicalTrials.gov · ChEMBL</div></div>{error && <div className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-600">{error}</div>}</div></header><div className="flex-1 overflow-y-auto"><div className="mx-auto max-w-4xl">{messages.map((message) => <ChatMessage key={message.id} message={message} />)}{isLoading && <div className="px-4 py-5"><div className="flex items-center gap-2 text-sm text-gray-500"><div className="h-2 w-2 animate-bounce rounded-full bg-purple-600" /><div className="h-2 w-2 animate-bounce rounded-full bg-purple-600 [animation-delay:-.3s]" /><div className="h-2 w-2 animate-bounce rounded-full bg-purple-600 [animation-delay:-.5s]" />Querying live sources…</div></div>}</div></div><ChatInput onSend={handleSendMessage} disabled={isLoading} /></div>;
}

export default App;
