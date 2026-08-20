import type { LucideIcon } from 'lucide-react';
import {
  ArrowRight,
  Atom,
  Beaker,
  BookOpenText,
  CheckCircle2,
  Database,
  Dna,
  FileSpreadsheet,
  FlaskConical,
  Network,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
} from 'lucide-react';
import type { Chat, SystemHealth } from '../types';
import { FileUpload } from './FileUpload';

interface ResearchHomeProps {
  health: SystemHealth | null;
  healthError?: string | null;
  loadedFiles: string[];
  chats: Chat[];
  onStartChat: (prompt?: string) => void;
  onOpenDocuments: () => void;
  onFileUpload: (filename: string) => void;
  onUploadError: (error: string) => void;
  onClearData: () => void;
  onSelectChat: (id: string) => void;
}

interface Workflow {
  title: string;
  description: string;
  prompt: string;
  sources: string;
  icon: LucideIcon;
}

const workflows: Workflow[] = [
  {
    title: 'Disease → genes',
    description: 'Rank genes associated with a disease using live Open Targets evidence.',
    prompt: 'What genes are associated with non-small-cell lung cancer?',
    sources: 'Open Targets',
    icon: Dna,
  },
  {
    title: 'Target → therapies',
    description: 'Find target-linked drug candidates, then cross-check approvals and trials.',
    prompt: 'Which FDA-approved drugs targeting EGFR also have recruiting Phase 3 trials for non-small-cell lung cancer?',
    sources: 'ChEMBL · FDA · ClinicalTrials.gov',
    icon: Target,
  },
  {
    title: 'Clinical-trial landscape',
    description: 'Search current trial records with phase, status, disease, and intervention filters.',
    prompt: 'List recruiting Phase 3 trials involving pembrolizumab for non-small-cell lung cancer.',
    sources: 'ClinicalTrials.gov · RxNorm',
    icon: FlaskConical,
  },
  {
    title: 'Drug evidence dossier',
    description: 'Resolve drug identity and inspect approval or label evidence from live sources.',
    prompt: 'What FDA approval information is available for pembrolizumab?',
    sources: 'RxNorm · Drugs@FDA/openFDA · DailyMed',
    icon: Beaker,
  },
  {
    title: 'Compound lookup',
    description: 'Retrieve current compound identifiers and chemical properties.',
    prompt: 'What are the PubChem compound properties of gefitinib?',
    sources: 'PubChem',
    icon: Atom,
  },
  {
    title: 'Ask a research question',
    description: 'Use the conversational layer for explanation, then move into typed evidence queries.',
    prompt: '',
    sources: 'GPT + live evidence when applicable',
    icon: Sparkles,
  },
];

function StatusPill({ health, healthError }: { health: SystemHealth | null; healthError?: string | null }) {
  if (healthError) {
    return <span className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">System status unavailable</span>;
  }
  if (!health) {
    return <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1.5 text-xs font-medium text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-400">Checking live system…</span>;
  }
  return <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"><span className="h-2 w-2 rounded-full bg-emerald-500" />Live system connected · {health.live_sources?.length || 7} sources</span>;
}

export function ResearchHome({
  health,
  healthError,
  loadedFiles,
  chats,
  onStartChat,
  onOpenDocuments,
  onFileUpload,
  onUploadError,
  onClearData,
  onSelectChat,
}: ResearchHomeProps) {
  return (
    <main className="scrollbar-subtle h-full overflow-y-auto bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.10),_transparent_34%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.08),_transparent_30%)] px-4 py-8 dark:bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.14),_transparent_34%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.08),_transparent_30%)] sm:px-6 lg:px-10">
      <div className="mx-auto max-w-7xl space-y-10">
        <section className="relative overflow-hidden rounded-[2rem] border border-slate-200/70 bg-white/85 p-7 shadow-[0_24px_80px_-40px_rgba(15,23,42,0.35)] backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/75 sm:p-10 lg:p-12">
          <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-indigo-200/30 blur-3xl dark:bg-indigo-600/10" />
          <div className="relative max-w-4xl">
            <div className="mb-5 flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-3 py-1.5 text-xs font-semibold text-white dark:bg-white dark:text-slate-950"><ShieldCheck className="h-3.5 w-3.5" />Evidence-first biomedical research</span>
              <StatusPill health={health} healthError={healthError} />
            </div>
            <h1 className="max-w-4xl text-4xl font-semibold tracking-[-0.035em] text-slate-950 dark:text-white sm:text-5xl lg:text-6xl">Ask a biomedical question. See the evidence path, not just an answer.</h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300 sm:text-lg">ChatAlchemy combines typed query planning, entity normalization, deterministic cross-source reasoning, claim verification, and live biomedical databases in one research workspace.</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <button onClick={() => onStartChat()} className="group inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-950/10 transition hover:-translate-y-0.5 hover:bg-slate-800 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-100">Start research <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" /></button>
              <button onClick={onOpenDocuments} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:-translate-y-0.5 hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-indigo-700 dark:hover:text-indigo-300"><BookOpenText className="h-4 w-4" />Analyze papers</button>
            </div>
          </div>
        </section>

        <section>
          <div className="mb-4 flex items-end justify-between gap-4">
            <div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600 dark:text-indigo-400">Research workflows</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">Start with a real task</h2></div>
            <div className="hidden text-sm text-slate-500 sm:block">Queries are routed to live sources when a typed evidence operation is available.</div>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {workflows.map(({ title, description, prompt, sources, icon: Icon }) => (
              <button key={title} onClick={() => onStartChat(prompt || undefined)} className="group rounded-2xl border border-slate-200/80 bg-white/80 p-5 text-left shadow-sm transition hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-950/5 dark:border-slate-800 dark:bg-slate-900/70 dark:hover:border-indigo-800">
                <div className="flex items-start justify-between gap-4"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300"><Icon className="h-5 w-5" /></span><ArrowRight className="h-4 w-4 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-indigo-500" /></div>
                <h3 className="mt-5 text-base font-semibold text-slate-900 dark:text-white">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-400">{description}</p>
                <p className="mt-4 text-xs font-medium text-slate-400 dark:text-slate-500">{sources}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-slate-200 bg-white/85 p-6 dark:border-slate-800 dark:bg-slate-900/70">
            <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600 dark:text-indigo-400">Your data</p><h2 className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">Combine local datasets with live evidence</h2></div><FileSpreadsheet className="h-6 w-6 text-slate-300" /></div>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-400">CSV files are parsed in your browser. Excel files are parsed through the backend, then the dataset is kept in this browser using IndexedDB. Candidate drug columns can be joined with FDA, trial, or target evidence.</p>
            <div className="mt-5 flex flex-wrap items-center gap-3"><FileUpload onUploadComplete={onFileUpload} onError={onUploadError} />{loadedFiles.length > 0 && <><span className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"><Database className="h-3.5 w-3.5" />{loadedFiles.length} dataset{loadedFiles.length === 1 ? '' : 's'} ready</span><button onClick={onClearData} className="text-xs font-medium text-rose-600 hover:text-rose-700 dark:text-rose-400">Clear local data</button></>}</div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-950 p-6 text-white dark:border-slate-800">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-indigo-300"><Network className="h-4 w-4" />Why this is a research system</div>
            <div className="mt-5 space-y-4 text-sm text-slate-300">
              <div className="flex gap-3"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" /><p><strong className="text-white">Evidence state:</strong> source IDs, URLs, qualifiers, retrieval traces, and claim support are carried with the answer.</p></div>
              <div className="flex gap-3"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" /><p><strong className="text-white">Deterministic joins:</strong> cross-source intersections are computed over normalized evidence rather than left entirely to model memory.</p></div>
              <div className="flex gap-3"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" /><p><strong className="text-white">Auditable failures:</strong> source errors are surfaced instead of silently replaced with unsupported biomedical claims.</p></div>
            </div>
          </div>
        </section>

        {chats.length > 0 && (
          <section>
            <div className="mb-4 flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600 dark:text-indigo-400">Recent work</p><h2 className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">Research sessions</h2></div></div>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {chats.slice(0, 6).map(chat => <button key={chat.id} onClick={() => onSelectChat(chat.id)} className="rounded-xl border border-slate-200 bg-white/80 p-4 text-left transition hover:border-indigo-200 hover:shadow-md dark:border-slate-800 dark:bg-slate-900/70"><div className="flex items-center gap-2"><Search className="h-4 w-4 text-indigo-500" /><span className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{chat.name}</span></div><p className="mt-2 text-xs text-slate-400">Updated {chat.updatedAt.toLocaleDateString()}</p></button>)}
            </div>
          </section>
        )}

        <section className="flex flex-col gap-3 border-t border-slate-200 py-6 text-xs leading-5 text-slate-500 dark:border-slate-800 dark:text-slate-400 sm:flex-row sm:items-start sm:justify-between">
          <p className="max-w-3xl"><strong className="font-semibold text-slate-700 dark:text-slate-300">Research use only.</strong> ChatAlchemy is an evidence exploration system, not a diagnostic, prescribing, or clinical decision-support tool. Verify consequential conclusions against the linked primary sources.</p>
          <p className="shrink-0">No bundled pharmaceutical knowledge base</p>
        </section>
      </div>
    </main>
  );
}
