import Papa from 'papaparse';
import * as XLSX from 'xlsx';

interface DataEntry {
  content: string;
  source: string;
  [key: string]: any;
}

let cachedData: DataEntry[] = [];
let userUploadedFiles: string[] = [];

async function processExcelFile(file: File): Promise<DataEntry[]> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet);

        resolve(
          jsonData
            .filter((row: any) => Object.values(row).some((value) => value != null && value !== ''))
            .map((row: any) => ({
              ...row,
              source: file.name,
              content: Object.entries(row)
                .filter(([_, value]) => value != null && value !== '')
                .map(([key, value]) => `${key}: ${value}`)
                .join(' | '),
            })),
        );
      } catch {
        reject(new Error('Error processing Excel file'));
      }
    };
    reader.onerror = () => reject(new Error('Error reading file'));
    reader.readAsArrayBuffer(file);
  });
}

async function processCsvFile(file: File): Promise<DataEntry[]> {
  const text = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve((e.target?.result as string) || '');
    reader.onerror = () => reject(new Error('Error reading file'));
    reader.readAsText(file);
  });

  return new Promise((resolve, reject) => {
    Papa.parse(text, {
      header: true,
      skipEmptyLines: true,
      transformHeader: (header) => header.trim(),
      complete: (results) => {
        const data = (results.data as any[])
          .filter((row) => Object.values(row).some((value) => value != null && value !== ''))
          .map((row) => ({
            ...row,
            source: file.name,
            content: Object.entries(row)
              .filter(([_, value]) => value != null && value !== '')
              .map(([key, value]) => `${key}: ${value}`)
              .join(' | '),
          }));
        resolve(data);
      },
      error: (error: Error) => reject(new Error(`Error parsing CSV: ${error.message}`)),
    });
  });
}

export async function processFile(file: File): Promise<DataEntry[]> {
  const extension = file.name.split('.').pop()?.toLowerCase();
  let data: DataEntry[];
  if (extension === 'xlsx' || extension === 'xls') data = await processExcelFile(file);
  else if (extension === 'csv') data = await processCsvFile(file);
  else throw new Error('Unsupported file format. Please upload CSV or Excel files.');

  userUploadedFiles = [...userUploadedFiles, file.name];
  cachedData = [...cachedData, ...data];
  return data;
}

export function clearData() {
  cachedData = [];
  userUploadedFiles = [];
}

export function getLoadedFiles(): string[] {
  return userUploadedFiles;
}

function extractConditions(query: string): { field: string; value: string }[] {
  const conditions: { field: string; value: string }[] = [];
  const matches = query.match(/where\s+(\w+)\s*[=:]\s*['"]?([^'"]+)['"]?/gi);
  matches?.forEach((match) => {
    const parsed = match.match(/where\s+(\w+)\s*[=:]\s*['"]?([^'"]+)['"]?/i);
    if (parsed?.[1] && parsed?.[2]) conditions.push({ field: parsed[1].toLowerCase(), value: parsed[2].trim() });
  });
  return conditions;
}

export async function searchKnowledgeBase(query: string): Promise<{
  text: string;
  matchCount: number;
  tableData?: { headers: string[]; rows: any[][]; caption?: string };
}> {
  if (cachedData.length === 0) return { text: '', matchCount: 0 };

  const queryLower = query.toLowerCase();
  const searchTerms = queryLower.split(/\s+/).filter((term) => term.length > 2);
  const conditions = extractConditions(query);
  const showTable = /\b(table|show|list|display)\b/i.test(query);

  const relevantEntries = cachedData.filter((entry) => {
    const content = entry.content.toLowerCase();
    const matchesSearch = searchTerms.length === 0 || searchTerms.some((term) => content.includes(term));
    const matchesConditions = conditions.every((condition) =>
      String(entry[condition.field] ?? '').toLowerCase().includes(condition.value.toLowerCase()),
    );
    return matchesSearch && matchesConditions;
  });

  if (relevantEntries.length === 0) return { text: '', matchCount: 0 };

  const text = relevantEntries
    .slice(0, 20)
    .map((entry) =>
      Object.entries(entry)
        .filter(([key]) => key !== 'content' && key !== 'source')
        .map(([key, value]) => `${key}: ${value}`)
        .join('\n'),
    )
    .join('\n\n');

  if (!showTable) return { text, matchCount: relevantEntries.length };

  const headers = Object.keys(relevantEntries[0]).filter((key) => key !== 'content' && key !== 'source');
  return {
    text,
    matchCount: relevantEntries.length,
    tableData: {
      headers,
      rows: relevantEntries.slice(0, 100).map((entry) => headers.map((header) => entry[header] ?? 'N/A')),
      caption: `Found ${relevantEntries.length} matching record${relevantEntries.length === 1 ? '' : 's'} in uploaded data`,
    },
  };
}
