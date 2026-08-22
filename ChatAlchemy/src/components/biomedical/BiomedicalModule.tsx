import { useCallback, useRef, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
import {
  BookOpenText,
  Download,
  FileText,
  Network,
  Search,
  ShieldCheck,
  UploadCloud,
  X,
} from 'lucide-react';
import { analyzeGeneDisease } from '../../lib/biomedical/analysis';
import { processFile } from '../../lib/biomedical/fileProcessing';
import { downloadBlob } from '../../lib/api';
import { ResultsViewer } from './ResultsViewer';
import { LoadingState } from './LoadingState';
import { ErrorBoundary } from './ErrorBoundary';
import { DocumentChatDrawer } from './DocumentChatDrawer';

cytoscape.use(cola);

interface Props { onTransferToChat?: () => void; }
interface DocState { name: string; genes: string[]; diseases: string[]; summary: string; }

export function BiomedicalModule({ onTransferToChat: _onTransferToChat }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  const [docs, setDocs] = useState<DocState[]>([]);
  const [query, setQuery] = useState('');
  const [drawerChatId, setDrawerChatId] = useState<string | null>(null);
  const cyRef = useRef<any>(null);
  const genes = [...new Set(docs.flatMap(doc => doc.genes))];
  const diseases = [...new Set(docs.flatMap(doc => doc.diseases))];

  const analyze = async (nextGenes: string[], q?: string, summary?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeGeneDisease({
        genes: nextGenes,
        query: q,
        suggestedDiseases: diseases,
        paperSummary: summary || docs[0]?.summary,
      });
      setResults(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Biomedical analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const onDrop = useCallback(async (files: File[]) => {
    setLoading(true);
    setError(null);
    try {
      const processed = await Promise.all(files.map(processFile));
      const incoming = processed.map((item, index) => ({
        name: files[index].name,
        genes: item.genes,
        diseases: item.suggestedDiseases,
        summary: item.summary,
      }));
      setDocs(previous => [...previous.filter(existing => !incoming.some(next => next.name === existing.name)), ...incoming]);
      const allGenes = [...new Set([...genes, ...incoming.flatMap(doc => doc.genes)])];
      if (allGenes.length) await analyze(allGenes, undefined, incoming[0]?.summary || docs[0]?.summary);
      else setError('No explicit gene symbols were extracted. You can still search a disease or gene manually.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not process document');
    } finally {
      setLoading(false);
    }
  }, [genes, diseases, docs]);

  const drop = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'text/plain': ['.txt'] },
    multiple: true,
  });

  const runSearch = async () => {
    const value = query.trim();
    if (!value) return;
    if (/^[A-Za-z][A-Za-z0-9-]{1,14}$/.test(value) && value === value.toUpperCase()) {
      await analyze([value.toUpperCase()]);
    } else {
      await analyze(genes, value);
    }
  };

  const removeDoc = (name: string) => {
    const next = docs.filter(doc => doc.name !== name);
    setDocs(next);
    if (!next.length) {
      setResults(null);
      setError(null);
      setDrawerChatId(null);
    }
  };

  const downloadGraph = () => {
    if (cyRef.current) {
      downloadBlob(
        cyRef.current.png({ full: true, scale: 2, output: 'blob' }),
        'chatalchemy-biomedical-network.png',
      );
    }
  };

  return (
    <ErrorBoundary>
      <div className="min-h-full bg-[radial-gradient(circle_at_top_right,_rgba(99,102,241,0.08),_transparent_32%)] bg-slate-50 px-4 py-7 dark:bg-slate-950 md:px-6 lg:px-10">
        <div className="mx-auto max-w-7xl space-y-6">
          <section className="rounded-[1.75rem] border border-slate-200 bg-white/85 p-7 shadow-[0_24px_70px_-48px_rgba(15,23,42,0.5)] backdrop-blur dark:border-slate-800 dark:bg-slate-900/80 sm:p-9">
            <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
              <div className="max-w-3xl">
                <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300"><BookOpenText className="h-3.5 w-3.5" />Document lab</div>
                <h1 className="text-3xl font-semibold tracking-tight text-slate-950 dark:text-white sm:text-4xl">Connect uploaded literature to live biomedical evidence.</h1>
                <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300 sm:text-base">Extract genes and disease context from PDF/TXT research documents, explore current Open Targets evidence, inspect networks, and continue the result in a side conversation without leaving the document workspace.</p>
              </div>
              <div className="max-w-sm rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-500 dark:border-slate-700 dark:bg-slate-950/50 dark:text-slate-400"><div className="mb-1 flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300"><ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />Data note</div>Uploaded document bytes are processed by the server. Extracted text may be sent to the configured server-side model for research synthesis. Do not upload protected health information.</div>
            </div>
          </section>

          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-6">
              <div className="mb-4 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300"><FileText className="h-5 w-5" /></span><div><h2 className="font-semibold text-slate-900 dark:text-white">Research documents</h2><p className="text-xs text-slate-400">PDF or plain text · multiple files supported</p></div></div>
              <div {...drop.getRootProps()} className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition ${drop.isDragActive ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/20' : 'border-slate-200 bg-slate-50/70 hover:border-indigo-300 hover:bg-indigo-50/40 dark:border-slate-700 dark:bg-slate-950/40 dark:hover:border-indigo-800'}`}>
                <input {...drop.getInputProps()} />
                <UploadCloud className="mx-auto mb-3 h-7 w-7 text-indigo-500" />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Drop PDF/TXT files here or click to browse</p>
                <p className="mt-1 text-xs text-slate-400">The app extracts paper context, genes, and suggested diseases.</p>
              </div>
              {!!docs.length && <div className="mt-4 space-y-2">{docs.map(doc => <div key={doc.name} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-950/40"><div className="min-w-0"><div className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{doc.name}</div><div className="mt-0.5 text-xs text-slate-400">{doc.genes.length} genes · {doc.diseases.length} diseases</div></div><button onClick={() => removeDoc(doc.name)} className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/30" aria-label={`Remove ${doc.name}`}><X className="h-4 w-4" /></button></div>)}</div>}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-6">
              <div className="mb-4 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300"><Search className="h-5 w-5" /></span><div><h2 className="font-semibold text-slate-900 dark:text-white">Explore genes or diseases</h2><p className="text-xs text-slate-400">Use a gene symbol or natural disease name</p></div></div>
              <div className="flex gap-2"><input value={query} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') void runSearch(); }} placeholder="e.g., EGFR or non-small-cell lung cancer" className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-900 outline-none transition focus:border-indigo-400 focus:ring-4 focus:ring-indigo-500/5 dark:border-slate-700 dark:bg-slate-950 dark:text-white" /><button onClick={() => void runSearch()} className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-100">Search</button></div>
              {!!genes.length && <div className="mt-5"><div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Extracted genes</div><div className="flex flex-wrap gap-2">{genes.slice(0, 40).map(gene => <button key={gene} onClick={() => void analyze([gene])} className="rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 transition hover:border-indigo-300 dark:border-indigo-900 dark:bg-indigo-950/30 dark:text-indigo-300">{gene}</button>)}</div></div>}
              {!!diseases.length && <div className="mt-5"><div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Suggested diseases</div><div className="flex flex-wrap gap-2">{diseases.slice(0, 20).map(disease => <button key={disease} onClick={() => void analyze(genes, disease)} className="rounded-full border border-rose-100 bg-rose-50 px-3 py-1.5 text-xs text-rose-700 transition hover:border-rose-300 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300">{disease}</button>)}</div></div>}
            </section>
          </div>

          {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300">{error}</div>}
          {loading && <LoadingState />}

          {results && !loading && <>
            <ResultsViewer results={results} onTransferToChat={setDrawerChatId} />
            {!!results.networkData?.length && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-6"><div className="mb-4 flex items-center justify-between"><div><h3 className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white"><Network className="h-5 w-5 text-indigo-600" />Evidence network</h3><p className="mt-1 text-xs text-slate-400">Interactive gene–disease–drug relationships from the current analysis.</p></div><button onClick={downloadGraph} title="Download network PNG" className="rounded-lg border border-slate-200 p-2 text-slate-500 transition hover:border-indigo-200 hover:text-indigo-600 dark:border-slate-700 dark:text-slate-300"><Download className="h-4 w-4" /></button></div><div className="h-[560px] overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800"><CytoscapeComponent elements={results.networkData} cy={(cy: any) => { cyRef.current = cy; }} style={{ width: '100%', height: '100%' }} layout={{ name: 'cola', nodeSpacing: 100, edgeLength: 140, animate: true, maxSimulationTime: 1800 }} stylesheet={[{ selector: 'node', style: { 'label': 'data(label)', 'background-color': '#6366f1', 'color': '#1f2937', 'text-wrap': 'wrap', 'text-max-width': '100px', 'font-size': '11px' } }, { selector: 'node[type="disease"]', style: { 'shape': 'diamond', 'background-color': '#e11d48' } }, { selector: 'node[type="drug"]', style: { 'shape': 'round-rectangle', 'background-color': '#059669' } }, { selector: 'edge', style: { 'width': 'data(weight)', 'line-color': '#9333ea', 'target-arrow-color': '#9333ea', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'label': 'data(label)', 'font-size': '9px' } }, { selector: 'edge[type="drug-gene"]', style: { 'line-color': '#059669', 'target-arrow-color': '#059669' } }, { selector: 'edge[type="disease-gene"]', style: { 'line-color': '#e11d48', 'target-arrow-color': '#e11d48', 'line-style': 'dashed' } }]} /></div><div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400"><span>● Gene</span><span className="text-rose-600">◆ Disease</span><span className="text-emerald-600">■ Drug</span></div></section>}
          </>}
        </div>
        <DocumentChatDrawer chatId={drawerChatId} onClose={() => setDrawerChatId(null)} />
      </div>
    </ErrorBoundary>
  );
}
