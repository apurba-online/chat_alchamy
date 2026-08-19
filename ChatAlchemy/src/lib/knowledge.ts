import Papa from 'papaparse';
import type { ChartData, DataEntry, SearchResult, TableData } from '../types';
import { parseSpreadsheet } from './api';

const DB_NAME = 'chatalchemy-data';
const STORE = 'datasets';
let cachedData: DataEntry[] = [];
let loadedFiles: string[] = [];
let initialized = false;
type StoredDataset = { name: string; rows: DataEntry[] };

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => { const db = req.result; if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'name' }); };
    req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error);
  });
}
async function persistDataset(dataset: StoredDataset) {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => { const tx = db.transaction(STORE, 'readwrite'); tx.objectStore(STORE).put(dataset); tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); });
  db.close();
}
async function readDatasets(): Promise<StoredDataset[]> {
  const db = await openDb();
  const result = await new Promise<StoredDataset[]>((resolve, reject) => { const req = db.transaction(STORE, 'readonly').objectStore(STORE).getAll(); req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error); });
  db.close(); return result;
}
export async function loadBackendData(): Promise<number> {
  if (initialized) return cachedData.length;
  initialized = true;
  try { const datasets = await readDatasets(); cachedData = datasets.flatMap(d => d.rows); loadedFiles = datasets.map(d => d.name); }
  catch { cachedData = []; loadedFiles = []; }
  return cachedData.length;
}
function normalizeRow(row: Record<string, unknown>, source: string, sheet?: string): DataEntry {
  const cleaned: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(row)) if (k !== '__sheet' && v !== null && v !== undefined && String(v).trim() !== '') cleaned[k.trim()] = v;
  return { ...cleaned, source, sheet, content: Object.entries(cleaned).map(([k, v]) => `${k}: ${String(v)}`).join(' | ') };
}
async function csvRows(file: File): Promise<DataEntry[]> {
  const text = await file.text();
  return new Promise((resolve, reject) => Papa.parse<Record<string, unknown>>(text, { header: true, skipEmptyLines: true, transformHeader: h => h.trim(), complete: r => resolve((r.data || []).map(row => normalizeRow(row, file.name)).filter(x => x.content)), error: (e: Error) => reject(e) }));
}
async function excelRows(file: File): Promise<DataEntry[]> {
  const parsed = await parseSpreadsheet(file);
  return parsed.rows.map(row => normalizeRow(row, file.name, typeof row.__sheet === 'string' ? row.__sheet : undefined)).filter(x => x.content);
}
export async function processFile(file: File): Promise<DataEntry[]> {
  await loadBackendData(); const ext = file.name.split('.').pop()?.toLowerCase(); let rows: DataEntry[];
  if (ext === 'csv') rows = await csvRows(file); else if (['xlsx', 'xls'].includes(ext || '')) rows = await excelRows(file); else throw new Error('Only CSV and Excel files are supported');
  if (!rows.length) throw new Error('No valid data found in file');
  cachedData = cachedData.filter(r => r.source !== file.name); cachedData.push(...rows); loadedFiles = [...loadedFiles.filter(x => x !== file.name), file.name]; await persistDataset({ name: file.name, rows }); return rows;
}
export async function clearData() {
  cachedData = []; loadedFiles = []; const db = await openDb(); await new Promise<void>((resolve, reject) => { const tx = db.transaction(STORE, 'readwrite'); tx.objectStore(STORE).clear(); tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); }); db.close();
}
export function getLoadedFiles() { return [...loadedFiles]; }
function allColumns(rows: DataEntry[]): string[] { const seen = new Set<string>(); rows.forEach(r => Object.keys(r).forEach(k => { if (!['content', 'source', 'sheet'].includes(k)) seen.add(k); })); return [...seen]; }
function findColumn(columns: string[], requested: string): string | undefined { const low = requested.trim().toLowerCase(); return columns.find(c => c.toLowerCase() === low) || columns.find(c => c.toLowerCase().includes(low)); }
function parseConditions(query: string, columns: string[]) { const out: Array<{ field: string; value: string }> = []; const regex = /(?:where|with)\s+([A-Za-z0-9 _.-]+?)\s*(?:=|:|is)\s*["']?([^,"']+?)["']?(?=\s+(?:and|$)|$)/gi; for (const m of query.matchAll(regex)) { const c = findColumn(columns, m[1]); if (c) out.push({ field: c, value: m[2].trim() }); } return out; }
function requestedColumns(query: string, columns: string[]): string[] { const m = query.match(/(?:show|select|display)\s+(?:columns?\s+)?(.+?)(?:\s+where|\s+with|$)/i); if (!m) return []; return m[1].split(/,|\band\b/i).map(x => findColumn(columns, x.trim())).filter((x): x is string => !!x); }
function numeric(value: unknown) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function aggregateBy(rows: DataEntry[], groupCol: string, valueCol?: string): { labels: string[]; values: number[]; label: string } { const groups = new Map<string, number[]>(); for (const r of rows) { const key = String(r[groupCol] ?? 'Unknown'); const arr = groups.get(key) || []; const n = valueCol ? numeric(r[valueCol]) : 1; if (n !== null) arr.push(n); groups.set(key, arr); } const labels = [...groups.keys()]; const values = labels.map(k => { const vals = groups.get(k) || []; return valueCol ? (vals.reduce((a, b) => a + b, 0) / (vals.length || 1)) : vals.length; }); return { labels, values, label: valueCol ? `Mean ${valueCol}` : 'Count' }; }
export async function searchKnowledgeBase(query: string): Promise<SearchResult> {
  await loadBackendData(); const columns = allColumns(cachedData); const conditions = parseConditions(query, columns); const reqCols = requestedColumns(query, columns); const low = query.toLowerCase(); const tokens = low.split(/\W+/).filter(t => t.length > 2 && !['show', 'list', 'table', 'chart', 'graph', 'plot', 'where', 'with', 'data', 'rows', 'records', 'count', 'first', 'last'].includes(t));
  let rows = cachedData.filter(r => conditions.every(c => String(r[c.field] ?? '').toLowerCase().includes(c.value.toLowerCase()))); if (!conditions.length && tokens.length) rows = rows.filter(r => tokens.some(t => r.content.toLowerCase().includes(t))); const nFirst = Number(low.match(/first\s+(\d+)/)?.[1] || 0); const nLast = Number(low.match(/last\s+(\d+)/)?.[1] || 0); if (nFirst) rows = rows.slice(0, nFirst); if (nLast) rows = rows.slice(-nLast);
  const countOnly = /\b(how many|count|number of)\b/.test(low) && !/(chart|graph|plot|table)/.test(low); const uniqueMatch = low.match(/unique\s+([a-z0-9 _.-]+)/i); let text = ''; let tableData: TableData | undefined; let chartData: ChartData | undefined;
  if (uniqueMatch) { const col = findColumn(columns, uniqueMatch[1]); if (col) { const vals = [...new Set(rows.map(r => String(r[col] ?? '')).filter(Boolean))]; text = `Found ${vals.length} unique value(s) in ${col}: ${vals.slice(0, 50).join(', ')}`; tableData = { headers: [col], rows: vals.map(v => [v]), caption: `Unique ${col}` }; } } else if (countOnly) text = `Found ${rows.length} matching record${rows.length === 1 ? '' : 's'} in uploaded data.`;
  const byMatch = query.match(/(?:by|group(?:ed)? by)\s+([A-Za-z0-9 _.-]+?)(?:\s|$)/i); const groupCol = byMatch ? findColumn(columns, byMatch[1]) : undefined;
  if (/\b(chart|graph|plot)\b/i.test(query) && rows.length) { const chartType: ChartData['type'] = low.includes('pie') ? 'pie' : low.includes('line') ? 'line' : 'bar'; const fallbackGroup = columns.find(c => rows.some(r => typeof r[c] === 'string')) || columns[0]; const group = groupCol || fallbackGroup; if (group) { const numericCol = columns.find(c => c !== group && rows.some(r => numeric(r[c]) !== null) && low.includes(c.toLowerCase())); const agg = aggregateBy(rows, group, numericCol); chartData = { type: chartType, labels: agg.labels.slice(0, 50), datasets: [{ label: agg.label, data: agg.values.slice(0, 50) }], title: `${agg.label} by ${group}` }; } }
  const wantsTable = /\b(table|show|list|display|rows|records)\b/i.test(query) || !!nFirst || !!nLast; if (wantsTable && rows.length && !tableData) { const headers = reqCols.length ? reqCols : columns; tableData = { headers, rows: rows.slice(0, 250).map(r => headers.map(h => r[h] ?? 'N/A')), caption: `${rows.length} matching record${rows.length === 1 ? '' : 's'} from uploaded data` }; }
  if (!text && rows.length) text = rows.slice(0, 20).map(r => Object.entries(r).filter(([k]) => !['content', 'source'].includes(k)).map(([k, v]) => `${k}: ${String(v)}`).join('\n')).join('\n\n');
  return { text, matchCount: rows.length, foundInKnowledgeBase: rows.length > 0, searchDetails: { totalRecords: cachedData.length, searchTerms: tokens, conditions, requestedColumns: reqCols, availableColumns: columns, sources: [...new Set(cachedData.map(r => r.source))] }, tableData, chartData };
}
export async function getCandidateDrugEvidence(limit = 40): Promise<Array<{ subject: string; predicate: string; value: string; qualifiers: Record<string, unknown> }>> { await loadBackendData(); if (!cachedData.length) return []; const columns = allColumns(cachedData); const preferred = ['drug name', 'drug', 'compound', 'compound name', 'molecule', 'medication', 'agent', 'name']; const col = preferred.map(p => findColumn(columns, p)).find(Boolean); if (!col) return []; const values = [...new Set(cachedData.map(r => String(r[col] ?? '').trim()).filter(v => v && v.length < 120))].slice(0, limit); return values.map(v => ({ subject: v, predicate: 'candidate_drug', value: v, qualifiers: { column: col, source: 'uploaded data' } })); }
