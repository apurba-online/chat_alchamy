import { useEffect, useState } from 'react';
import {
  ArrowRight,
  BookOpenText,
  Brain,
  Database,
  Network,
  Waypoints,
} from 'lucide-react';
import { createNewChat, getChatById, saveChat } from '../../lib/storage';
import { DataTable } from '../DataTable';

interface Results {
  genes?: string[];
  explanation: string;
  paperSummary?: string;
  tableData?: { headers: string[]; rows: unknown[][]; caption?: string };
  clusters?: Array<{ id: number; genes: string[]; description?: string }>;
  diseaseEvidenceSummary?: Array<{
    term: string;
    genes: string[];
    supportCount: number;
    meanAssociationScore: number;
  }>;
  evidence?: Array<{ source: string; source_record_id?: string }>;
}

function suggestions(results: Results): string[] {
  const genes = (results.genes || []).slice(0, 4).join(', ');
  return [
    genes ? `What FDA-approved drugs target ${genes}?` : 'What approved drugs are relevant to these findings?',
    'Which findings have recruiting Phase 3 clinical trials?',
    'How do the live database results compare with the uploaded paper?',
  ];
}

export function ResultsViewer({
  results,
  onTransferToChat,
}: {
  results: Results;
  onTransferToChat?: (chatId: string) => void;
}) {
  const [moving, setMoving] = useState(false);
  const [documentChatId, setDocumentChatId] = useState<string | null>(null);
  const uniqueSources = [...new Set((results.evidence || []).map(item => item.source).filter(Boolean))];
  const resultIdentity = `${results.paperSummary || ''}|${(results.genes || []).join('|')}`;

  useEffect(() => {
    setDocumentChatId(null);
  }, [resultIdentity]);

  const transfer = () => {
    setMoving(true);
    try {
      if (documentChatId && getChatById(documentChatId)) {
        onTransferToChat?.(documentChatId);
        return;
      }

      const chat = createNewChat('Document Evidence Analysis');
      const diseaseSummary = (results.diseaseEvidenceSummary || [])
        .slice(0, 10)
        .map(item => `- ${item.term}: ${item.supportCount} retrieved gene(s); mean Open Targets association score=${item.meanAssociationScore.toFixed(3)}; genes=${item.genes.join(', ')}`)
        .join('\n');
      const context = `# Document Evidence Context\n\n${results.paperSummary ? `## Literature Summary\n${results.paperSummary}\n\n` : ''}## Live Evidence Analysis\n${results.explanation}\n\n## Genes\n${(results.genes || []).join(', ') || 'None'}\n\n## Shared disease evidence\n${diseaseSummary || 'No shared disease evidence summary'}\n\nThis context came from ChatAlchemy Document Lab and its live evidence workflow. The shared-disease section is a descriptive summary of retrieved Open Targets associations, not a statistical enrichment test.`;
      chat.analysisContext = {
        genes: results.genes || [],
        paperSummary: results.paperSummary || '',
        diseaseEvidenceSummary: results.diseaseEvidenceSummary || [],
      };
      chat.messages = [
        { id: crypto.randomUUID(), role: 'assistant', content: context, timestamp: new Date() },
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Suggested follow-up questions:\n\n${suggestions(results).map((question, index) => `[Q${index + 1}] ${question}`).join('\n\n')}`,
          timestamp: new Date(),
        },
      ];
      saveChat(chat);
      setDocumentChatId(chat.id);
      onTransferToChat?.(chat.id);
    } finally {
      setMoving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-900 dark:text-white">Document analysis ready</div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span>{results.genes?.length || 0} genes</span>
            <span>·</span>
            <span>{results.diseaseEvidenceSummary?.length || 0} shared disease records</span>
            {uniqueSources.length > 0 && <><span>·</span><span className="inline-flex items-center gap-1"><Database className="h-3 w-3" />{uniqueSources.join(', ')}</span></>}
          </div>
        </div>
        <button onClick={transfer} disabled={moving} className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-100">
          {moving ? 'Opening side chat…' : 'Continue in research chat'}
          {!moving && <ArrowRight className="h-4 w-4" />}
        </button>
      </div>

      {results.tableData && <DataTable {...results.tableData} />}

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-300"><BookOpenText className="h-4 w-4 text-indigo-500" />Literature context</h3>
          <p className="whitespace-pre-line text-sm leading-7 text-slate-700 dark:text-slate-300">{results.paperSummary || 'No uploaded-paper summary is active for this analysis.'}</p>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-300"><Brain className="h-4 w-4 text-violet-500" />Evidence synthesis</h3>
          <p className="text-sm leading-7 text-slate-700 dark:text-slate-300">{results.explanation}</p>
        </section>
      </div>

      {!!results.clusters?.length && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white"><Network className="h-5 w-5 text-indigo-500" />Gene profile groups</h3>
          <p className="mb-4 text-xs leading-5 text-slate-400">These groups are a descriptive heuristic based on overlap in retrieved Open Targets disease-association profiles; they are not unsupervised biological clusters.</p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {results.clusters.map(cluster => <div key={cluster.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/40"><div className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">Group {cluster.id}</div><div className="flex flex-wrap gap-1.5">{cluster.genes.map(gene => <span key={gene} className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">{gene}</span>)}</div>{cluster.description && <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">{cluster.description}</p>}</div>)}
          </div>
        </section>
      )}

      {!!results.diseaseEvidenceSummary?.length && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-2 flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white"><Waypoints className="h-5 w-5 text-indigo-500" />Shared disease evidence</h3>
          <p className="mb-4 text-xs leading-5 text-slate-400">Descriptive summary of disease associations retrieved for the current genes. No statistical enrichment p-values are reported without a validated background universe.</p>
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
            {results.diseaseEvidenceSummary.slice(0, 15).map((result, index) => <div key={result.term} className={`flex flex-col justify-between gap-2 px-4 py-3 text-sm md:flex-row md:items-center ${index ? 'border-t border-slate-100 dark:border-slate-800' : ''}`}><span className="font-medium text-slate-800 dark:text-slate-100">{result.term}</span><span className="text-xs text-slate-500 dark:text-slate-400">{result.supportCount} retrieved gene{result.supportCount === 1 ? '' : 's'} · mean score {result.meanAssociationScore.toFixed(3)} · {result.genes.join(', ')}</span></div>)}
          </div>
        </section>
      )}
    </div>
  );
}
