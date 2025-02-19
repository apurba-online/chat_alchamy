import Papa from 'papaparse';
import * as XLSX from 'xlsx';

interface DataEntry {
  content: string;
  source: string;
  [key: string]: any;
}

let cachedData: DataEntry[] = [];
let isPharmAlchemyLoaded = false;
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

        const processedData = jsonData
          .filter((row: any) => Object.values(row).some(value => value != null && value !== ''))
          .map((row: any) => ({
            ...row,
            source: file.name,
            content: Object.entries(row)
              .filter(([_, value]) => value != null && value !== '')
              .map(([key, value]) => `${key}: ${value}`)
              .join(' | ')
          }));

        resolve(processedData);
      } catch (error) {
        reject(new Error('Error processing Excel file'));
      }
    };
    reader.onerror = () => reject(new Error('Error reading file'));
    reader.readAsArrayBuffer(file);
  });
}

async function processCsvFile(file: File | string): Promise<DataEntry[]> {
  try {
    let text: string;
    if (typeof file === 'string') {
      const response = await fetch(`/data/${file}`);
      if (!response.ok) {
        throw new Error(`File ${file} not found or inaccessible`);
      }
      text = await response.text();
    } else {
      text = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = (e) => reject(new Error('Error reading file'));
        reader.readAsText(file);
      });
    }

    return new Promise((resolve, reject) => {
      Papa.parse(text, {
        header: true,
        skipEmptyLines: true,
        transformHeader: (header) => header.trim(),
        complete: (results) => {
          if (results.errors.length > 0) {
            console.warn('CSV parsing warnings:', results.errors);
          }
          const data = results.data
            .filter((row: any) => Object.values(row).some(value => value != null && value !== ''))
            .map((row: any) => ({
              ...row,
              source: typeof file === 'string' ? 'PharmAlchemy' : file.name,
              content: Object.entries(row)
                .filter(([_, value]) => value != null && value !== '')
                .map(([key, value]) => `${key}: ${value}`)
                .join(' | ')
            }));
          
          resolve(data);
        },
        error: (error) => {
          reject(new Error(`Error parsing CSV: ${error}`));
        }
      });
    });
  } catch (error) {
    console.error(`Error processing file:`, error);
    throw error;
  }
}

export async function processFile(file: File): Promise<DataEntry[]> {
  const fileExtension = file.name.split('.').pop()?.toLowerCase();
  let data: DataEntry[];

  try {
    if (fileExtension === 'xlsx' || fileExtension === 'xls') {
      data = await processExcelFile(file);
    } else if (fileExtension === 'csv') {
      data = await processCsvFile(file);
    } else {
      throw new Error('Unsupported file format. Please upload CSV or Excel files.');
    }

    userUploadedFiles.push(file.name);
    cachedData = [...cachedData, ...data];
    return data;
  } catch (error) {
    throw error;
  }
}

export async function loadBackendData() {
  try {
    const data = await processCsvFile('ttd_drug_disease.csv');
    if (data.length > 0) {
      cachedData = data;
      isPharmAlchemyLoaded = true;
      return data.length;
    }
    return 0;
  } catch (error) {
    console.error('Error loading backend data:', error);
    return 0;
  }
}

export function clearData() {
  cachedData = cachedData.filter(entry => entry.source === 'PharmAlchemy');
  userUploadedFiles = [];
  return true;
}

export function getLoadedFiles(): string[] {
  // Only return user-uploaded files for the count display
  return userUploadedFiles;
}

function extractConditions(query: string): { field: string; value: string }[] {
  const conditions: { field: string; value: string }[] = [];
  const whereMatches = query.match(/where\s+(\w+)\s*[=:]\s*['"]?([^'"]+)['"]?/gi);
  
  if (whereMatches) {
    whereMatches.forEach(match => {
      const [_, field, value] = match.match(/where\s+(\w+)\s*[=:]\s*['"]?([^'"]+)['"]?/i) || [];
      if (field && value) {
        conditions.push({ field: field.toLowerCase(), value: value.trim() });
      }
    });
  }
  return conditions;
}

function extractColumns(query: string): string[] {
  const columnMatch = query.match(/show\s+(?:columns?|fields?)\s+([^where]+)(?:\s+where|$)/i);
  if (columnMatch) {
    return columnMatch[1]
      .split(/[,\s]+/)
      .map(col => col.trim())
      .filter(col => col.length > 0)
      .map(col => col.toLowerCase());
  }
  return [];
}

export async function searchKnowledgeBase(query: string): Promise<{
  text: string;
  foundInKnowledgeBase: boolean;
  tableData?: {
    headers: string[];
    rows: any[][];
    caption?: string;
  };
}> {
  const queryLower = query.toLowerCase();
  const searchTerms = queryLower.split(' ').filter(term => term.length > 2);
  const showTable = queryLower.includes('table') || 
                   queryLower.includes('show') || 
                   queryLower.includes('list') ||
                   queryLower.includes('display');
  
  // Extract conditions and columns from the query
  const conditions = extractConditions(query);
  const requestedColumns = extractColumns(query);
  
  // Find relevant entries
  let relevantEntries = cachedData.filter(entry => {
    const content = entry.content.toLowerCase();
    const matchesSearch = searchTerms.some(term => content.includes(term));
    
    // Apply conditions if they exist
    const matchesConditions = conditions.length === 0 || conditions.every(condition => {
      const entryValue = String(entry[condition.field] || '').toLowerCase();
      return entryValue.includes(condition.value.toLowerCase());
    });
    
    return matchesSearch && matchesConditions;
  });

  if (relevantEntries.length === 0) {
    return {
      text: "",
      foundInKnowledgeBase: false
    };
  }

  // Format the text response without markdown
  const formattedText = relevantEntries.map(entry => 
    Object.entries(entry)
      .filter(([key]) => key !== 'content' && key !== 'source')
      .map(([key, value]) => `${key}: ${value}`)
      .join('\n')
  ).join('\n\n');

  // Only include table data if explicitly requested
  let tableData;
  if (showTable) {
    // Determine which headers to show
    let headers = Object.keys(relevantEntries[0])
      .filter(key => key !== 'content' && key !== 'source');
    
    // Filter headers if specific columns were requested
    if (requestedColumns.length > 0) {
      headers = headers.filter(header => 
        requestedColumns.includes(header.toLowerCase())
      );
    }
    
    tableData = {
      headers,
      rows: relevantEntries.map(entry => 
        headers.map(header => entry[header] || 'N/A')
      ),
      caption: `Found ${relevantEntries.length} matching records${
        conditions.length > 0 
          ? ` with ${conditions.map(c => `${c.field}=${c.value}`).join(', ')}` 
          : ''
      }`
    };
  }

  return {
    text: formattedText,
    foundInKnowledgeBase: isPharmAlchemyLoaded && relevantEntries[0].source === 'PharmAlchemy',
    tableData: showTable ? tableData : undefined
  };
}