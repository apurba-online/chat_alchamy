import { useEffect, useRef, useState } from 'react';
import { BookOpenText, Loader2, X } from 'lucide-react';
import type { Chat, Message, QueryResponse } from '../../types';
import { queryLive } from '../../lib/api';
import { getChatById, saveChat } from '../../lib/storage';
import { ChatInput } from '../ChatInput';
import { ChatMessage } from '../ChatMessage';

const newId = () => crypto.randomUUID();

function responseMessage(data: QueryResponse): Message {
  const seen = new Set<string>();
  const provenance = (data.evidence || [])
    .filter(item => {
      const key = `${item.source}:${item.source_record_id || item.id}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map(item => ({
      id: item.id,
      source: item.source,
      recordId: item.source_record_id,
      url: item.source_url,
    }));

  return {
    id: newId(),
    role: 'assistant',
    content: data.answer,
    timestamp: new Date(),
    supportRate: data.supported_claim_rate,
    warnings: data.warnings,
    tableData: data.table || undefined,
    chartData: data.chart || undefined,
    provenance,
    evidenceCount: data.evidence?.length || 0,
    evidenceRecords: (data.evidence || []).map(item => ({
      id: item.id,
      subject: item.subject,
      predicate: item.predicate,
      value: item.value,
      qualifiers: item.qualifiers,
      source: item.source,
      recordId: item.source_record_id,
      url: item.source_url,
      retrievedAt: item.retrieved_at,
      sourceVersion: item.source_version,
      evidenceType: item.evidence_type,
    })),
    planIntent: data.plan?.intent,
    claims: (data.claims || []).map(claim => ({
      text: claim.text,
      supportIds: claim.support_ids || [],
      supported: Boolean(claim.supported),
    })),
    traces: (data.traces || []).map(trace => ({
      source: trace.source,
      operation: trace.operation,
      ok: trace.ok,
      latencyMs: trace.latency_ms,
      resultCount: trace.result_count,
      error: trace.error,
    })),
    conflicts: (data.conflicts || []).map(conflict => ({
      relation: conflict.relation,
      reason: conflict.reason,
    })),
  };
}

export function DocumentChatDrawer({
  chatId,
  onClose,
}: {
  chatId: string | null;
  onClose: () => void;
}) {
  const [chat, setChat] = useState<Chat | null>(null);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setChat(chatId ? getChatById(chatId) : null);
  }, [chatId]);

  useEffect(() => {
    if (!chatId) return;
    const frame = window.requestAnimationFrame(() => {
      const scroller = scrollRef.current;
      if (scroller) scroller.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [chatId, chat?.messages.length, loading]);

  useEffect(() => {
    if (!chatId) return;
    const keyHandler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', keyHandler);
    return () => window.removeEventListener('keydown', keyHandler);
  }, [chatId, onClose]);

  const send = async (content: string) => {
    if (!chat || loading) return;

    const user: Message = {
      id: newId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    let next: Chat = {
      ...chat,
      messages: [...chat.messages, user],
      updatedAt: new Date(),
    };
    setChat(next);
    saveChat(next);
    setLoading(true);

    try {
      const conversation = next.messages.slice(-10).map(message => ({
        role: message.role,
        content: message.content,
      }));
      const data = await queryLive(content, conversation, []);
      next = {
        ...next,
        messages: [...next.messages, responseMessage(data)],
        updatedAt: new Date(),
      };
    } catch (err) {
      const warning = err instanceof Error ? err.message : 'Unknown request error';
      next = {
        ...next,
        messages: [
          ...next.messages,
          {
            id: newId(),
            role: 'assistant',
            content: 'I could not complete that follow-up workflow. The Document Lab remains open, and I did not replace the failed evidence path with an unsupported biomedical answer.',
            timestamp: new Date(),
            warnings: [warning],
          },
        ],
        updatedAt: new Date(),
      };
    } finally {
      setChat(next);
      saveChat(next);
      setLoading(false);
    }
  };

  if (!chatId || !chat) return null;

  return (
    <div className="fixed inset-0 z-[70] flex justify-end">
      <button
        className="absolute inset-0 cursor-default bg-slate-950/20 backdrop-blur-[1px]"
        onClick={onClose}
        aria-label="Close document research chat"
      />
      <aside className="relative flex h-full w-full max-w-xl flex-col border-l border-slate-200 bg-slate-50 shadow-2xl dark:border-slate-800 dark:bg-slate-950">
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
              <BookOpenText className="h-4 w-4 text-indigo-500" />
              Document research chat
            </div>
            <p className="mt-1 text-xs text-slate-400">Your document analysis remains open behind this drawer.</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label="Close document research chat"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div ref={scrollRef} className="scrollbar-subtle min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <div className="mx-auto w-full px-4 pb-8 pt-2 sm:px-5">
            {chat.messages.map(message => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {loading && (
              <div className="my-5 flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
                Working through the evidence path…
              </div>
            )}
          </div>
        </div>

        <div className="shrink-0">
          <ChatInput onSend={message => void send(message)} disabled={loading} />
        </div>
      </aside>
    </div>
  );
}
