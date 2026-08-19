import React from 'react';
import { User, FlaskRound as Flask, ExternalLink, ShieldCheck } from 'lucide-react';
import { Message } from '../types';

interface ChatMessageProps { message: Message; }

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  return (
    <div className={`py-7 ${isUser ? 'bg-white/50' : 'bg-white/80'}`}>
      <div className="max-w-4xl mx-auto flex gap-5 px-4">
        <div className="w-8 h-8 flex-shrink-0">{isUser ? <User className="w-full h-full text-gray-600" /> : <Flask className="w-full h-full text-purple-600" />}</div>
        <div className="flex-1 min-w-0 space-y-3">
          <div className="flex items-center gap-3"><p className="font-medium text-sm text-gray-600">{isUser ? 'You' : 'ChatAlchemy-Live'}</p>{!isUser && message.supportRate !== undefined && <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700"><ShieldCheck className="h-3.5 w-3.5" />{Math.round(message.supportRate * 100)}% claim support</span>}</div>
          <div className="prose prose-purple max-w-none whitespace-pre-wrap text-gray-800">{message.content}</div>
          {!isUser && message.provenance && message.provenance.length > 0 && <div className="rounded-xl border border-gray-200 bg-gray-50 p-3"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Live provenance</p><div className="flex flex-wrap gap-2">{message.provenance.slice(0, 12).map((item) => item.url ? <a key={item.id} href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border bg-white px-2.5 py-1.5 text-xs text-gray-700 hover:border-purple-300 hover:text-purple-700">{item.source}{item.recordId ? ` · ${item.recordId}` : ''}<ExternalLink className="h-3 w-3" /></a> : <span key={item.id} className="rounded-lg border bg-white px-2.5 py-1.5 text-xs text-gray-700">{item.source}{item.recordId ? ` · ${item.recordId}` : ''}</span>)}</div></div>}
          {!isUser && message.warnings && message.warnings.length > 0 && <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">{message.warnings.join(' ')}</div>}
        </div>
      </div>
    </div>
  );
}
