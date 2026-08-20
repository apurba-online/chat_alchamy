import { useState } from 'react';
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleSlash2,
  Clock3,
  Database,
  ExternalLink,
  FlaskConical,
  Route,
  ShieldCheck,
  User,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Message } from '../types';
import { DataTable } from './DataTable';
import { DataVisualization } from './DataVisualization';

const intentLabels: Record<string, string> = {
  identity: 'Drug identity',
  label: 'Drug label',
  approval: 'FDA approval',
  trials: 'Clinical trials',
  target_drugs: 'Target → drugs',
  gene: 'Gene evidence',
  disease: 'Disease → genes',
  compound: 'Compound lookup',
  cross_source: 'Cross-source join',
  general: 'Model synthesis',
  local_data: 'Local dataset',
};

function formatLatency(ms: number): string {
  if (!Number.isFinite(ms)) return '—';
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function ChatMessage({ message }: { message: Message; darkMode?: boolean }) {
  const isUser = message.role === 'user';
  const [showEvidence, setShowEvidence] = useState(false);
  const hasEvidence = Boolean(message.provenance?.length || message.evidenceCount);
  const supportedClaims = message.claims?.filter(claim => claim.supported).length || 0;
  const totalClaims = message.claims?.length || 0;
  const failedTraces = message.traces?.filter(trace => !trace.ok) || [];
  const successfulTraces = message.traces?.filter(trace => trace.ok) || [];
  const routeLabel = message.planIntent ? intentLabels[message.planIntent] || message.planIntent : null;
  const clickQuestion = (line: string) =>
    window.dispatchEvent(
      new CustomEvent('question-click', {
        detail: { question: line.replace(/^\[Q\d+\]\s*/, '').trim() },
      }),
    );

  if (isUser) {
    return (
      <div className="my-5 flex justify-end">
        <div className="max-w-[88%] rounded-2xl rounded-br-md bg-slate-950 px-4 py-3 text-sm leading-6 text-white shadow-sm dark:bg-slate-100 dark:text-slate-950 sm:max-w-[78%]">
          <div className="mb-1 flex items-center justify-end gap-1.5 text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">
            <User className="h-3 w-3" />You
          </div>
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      </div>
    );
  }

  return (
    <article className="my-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_14px_40px_-32px_rgba(15,23,42,0.45)] dark:border-slate-800 dark:bg-slate-900">
      <div className="p-5 sm:p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300">
              <FlaskConical className="h-4 w-4" />
            </span>
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-white">ChatAlchemy</div>
              {routeLabel && <div className="text-[11px] text-slate-400">{routeLabel}</div>}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {hasEvidence && totalClaims > 0 && (
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${supportedClaims === totalClaims ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300' : 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'}`}>
                <ShieldCheck className="h-3.5 w-3.5" />
                {supportedClaims}/{totalClaims} claims supported
              </span>
            )}
            {hasEvidence && totalClaims === 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                <Database className="h-3.5 w-3.5" />Evidence retrieved
              </span>
            )}
            {!hasEvidence && message.planIntent === 'general' && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700 dark:bg-violet-950/40 dark:text-violet-300">
                <Bot className="h-3.5 w-3.5" />Model synthesis
              </span>
            )}
            {failedTraces.length > 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                <CircleSlash2 className="h-3.5 w-3.5" />{failedTraces.length} source issue{failedTraces.length === 1 ? '' : 's'}
              </span>
            )}
          </div>
        </div>

        <div className="prose prose-slate max-w-none text-sm leading-7 dark:prose-invert sm:text-[15px]">
          {message.content.split('\n').map((line, index) =>
            /^\[Q\d+\]/.test(line) ? (
              <button
                key={index}
                onClick={() => clickQuestion(line)}
                className="mb-2 block w-full rounded-xl border border-indigo-100 bg-indigo-50/50 p-3 text-left text-sm font-medium text-indigo-700 transition hover:border-indigo-200 hover:bg-indigo-50 dark:border-indigo-900 dark:bg-indigo-950/20 dark:text-indigo-300 dark:hover:bg-indigo-950/40"
              >
                {line}
              </button>
            ) : (
              <ReactMarkdown key={index}>{line}</ReactMarkdown>
            ),
          )}
        </div>

        {message.tableData && <div className="mt-5"><DataTable {...message.tableData} /></div>}
        {message.chartData && <div className="mt-5"><DataVisualization data={message.chartData} /></div>}

        {message.warnings?.length ? (
          <div className="mt-5 flex gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{message.warnings.join(' ')}</span>
          </div>
        ) : null}
      </div>

      {(hasEvidence || message.traces?.length || message.conflicts?.length) && (
        <div className="border-t border-slate-200 bg-slate-50/70 dark:border-slate-800 dark:bg-slate-950/35">
          <button
            onClick={() => setShowEvidence(value => !value)}
            className="flex w-full items-center justify-between gap-4 px-5 py-3 text-left text-xs font-semibold text-slate-600 transition hover:bg-slate-100/80 dark:text-slate-300 dark:hover:bg-slate-800/50 sm:px-6"
          >
            <span className="flex items-center gap-2"><Database className="h-3.5 w-3.5" />Evidence & provenance {message.evidenceCount ? `· ${message.evidenceCount} evidence item${message.evidenceCount === 1 ? '' : 's'}` : ''}</span>
            {showEvidence ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {showEvidence && (
            <div className="grid gap-5 border-t border-slate-200 px-5 py-5 dark:border-slate-800 sm:px-6 lg:grid-cols-2">
              <section>
                <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400"><ExternalLink className="h-3.5 w-3.5" />Live records</h4>
                <div className="mt-3 flex flex-wrap gap-2">
                  {message.provenance?.length ? message.provenance.map(item =>
                    item.url ? (
                      <a key={`${item.source}-${item.recordId || item.id}`} href={item.url} target="_blank" rel="noreferrer" className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-600 transition hover:border-indigo-200 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-indigo-800 dark:hover:text-indigo-300">
                        <span className="truncate">{item.source}{item.recordId ? ` · ${item.recordId}` : ''}</span><ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <span key={`${item.source}-${item.recordId || item.id}`} className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">{item.source}</span>
                    ),
                  ) : <span className="text-xs text-slate-400">No linkable source records were returned.</span>}
                </div>
              </section>

              <section>
                <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400"><Route className="h-3.5 w-3.5" />Execution trace</h4>
                <div className="mt-3 space-y-2">
                  {message.traces?.length ? message.traces.map((trace, index) => (
                    <div key={`${trace.source}-${trace.operation}-${index}`} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs dark:border-slate-700 dark:bg-slate-900">
                      <div className="min-w-0"><div className="flex items-center gap-1.5 font-medium text-slate-700 dark:text-slate-200">{trace.ok ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> : <CircleSlash2 className="h-3.5 w-3.5 text-rose-500" />}{trace.source}</div><div className="mt-0.5 truncate text-slate-400">{trace.operation}{trace.error ? ` · ${trace.error}` : ''}</div></div>
                      <div className="shrink-0 text-right text-slate-400"><div>{trace.resultCount} result{trace.resultCount === 1 ? '' : 's'}</div><div className="mt-0.5 flex items-center justify-end gap-1"><Clock3 className="h-3 w-3" />{formatLatency(trace.latencyMs)}</div></div>
                    </div>
                  )) : <span className="text-xs text-slate-400">No external source trace for this response.</span>}
                </div>
              </section>

              {message.claims?.length ? (
                <section className="lg:col-span-2">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Claim verification</h4>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    {message.claims.map((claim, index) => <div key={index} className="flex gap-2 rounded-lg border border-slate-200 bg-white p-3 text-xs leading-5 text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">{claim.supported ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" /> : <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />}<span>{claim.text}</span></div>)}
                  </div>
                </section>
              ) : null}

              {message.conflicts?.length ? (
                <section className="lg:col-span-2">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Evidence relations</h4>
                  <div className="mt-3 flex flex-wrap gap-2">{message.conflicts.slice(0, 12).map((conflict, index) => <span key={index} title={conflict.reason} className="rounded-full border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">{conflict.relation.replaceAll('_', ' ')}</span>)}</div>
                </section>
              ) : null}
            </div>
          )}
        </div>
      )}
    </article>
  );
}
