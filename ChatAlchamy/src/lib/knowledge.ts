import Papa from 'papaparse';
import * as XLSX from 'xlsx';

interface DataEntry {
  content: string;
  source: string;
  [key: string]: any;
}

let cachedData: DataEntry[] = [];

// Function to process CSV files
async function processCsvFile(filename: string): Promise<DataEntry[]> {
  try {
    const response = await fetch(`/data/${filename}`);
    const text = await response.text();
    const { data } = Papa.parse(text, { header: true });
    
    return data.map((row: any) => ({
      ...row,
      source: filename,
      content: Object.entries(row)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ')
    }));
  } catch (error) {
    console.error(`Error loading ${filename}:`, error);
    return [];
  }
}

// Function to process Excel files
async function processExcelFile(filename: string): Promise<DataEntry[]> {
  try {
    const response = await fetch(`/data/${filename}`);
    const arrayBuffer = await response.arrayBuffer();
    const data = new Uint8Array(arrayBuffer);
    const workbook = XLSX.read(data, { type: 'array' });
    
    const firstSheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[firstSheetName];
    const jsonData = XLSX.utils.sheet_to_json(worksheet);
    
    return jsonData.map((row: any) => ({
      ...row,
      source: filename,
      content: Object.entries(row)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ')
    }));
  } catch (error) {
    console.error(`Error loading ${filename}:`, error);
    return [];
  }
}

// Function to process a file based on its extension
async function processFile(filename: string): Promise<DataEntry[]> {
  const extension = filename.split('.').pop()?.toLowerCase();
  
  if (extension === 'csv') {
    return processCsvFile(filename);
  } else if (extension === 'xlsx' || extension === 'xls') {
    return processExcelFile(filename);
  }
  
  return [];
}

// Function to list all files in the data directory
async function listDataFiles(): Promise<string[]> {
  try {
    const response = await fetch('/data');
    const text = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, 'text/html');
    const links = Array.from(doc.querySelectorAll('a'));
    
    return links
      .map(link => link.getAttribute('href'))
      .filter((href): href is string => 
        href !== null && 
        href !== '../' && 
        (href.endsWith('.csv') || href.endsWith('.xlsx') || href.endsWith('.xls'))
      );
  } catch (error) {
    console.error('Error listing data files:', error);
    return [];
  }
}

// Load all knowledge base files
async function loadKnowledgeBaseFiles() {
  try {
    const files = await listDataFiles();
    
    if (files.length === 0) {
      console.warn('No data files found in /data directory');
      cachedData = sampleData.map(row => ({
        ...row,
        source: 'sample_data',
        content: Object.entries(row)
          .map(([key, value]) => `${key}: ${value}`)
          .join(', ')
      }));
      return;
    }

    const dataPromises = files.map(processFile);
    const results = await Promise.all(dataPromises);
    cachedData = results.flat();

    if (cachedData.length === 0) {
      // Fallback to sample data if no files could be loaded
      cachedData = sampleData.map(row => ({
        ...row,
        source: 'sample_data',
        content: Object.entries(row)
          .map(([key, value]) => `${key}: ${value}`)
          .join(', ')
      }));
    }
  } catch (error) {
    console.error('Error loading knowledge base:', error);
    cachedData = sampleData.map(row => ({
      ...row,
      source: 'sample_data',
      content: Object.entries(row)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ')
    }));
  }
}

// Sample data as fallback
const sampleData = [
  {
    month: 'January',
    sales: 1000,
    revenue: 50000
  },
  {
    month: 'February',
    sales: 1200,
    revenue: 60000
  },
  {
    month: 'March',
    sales: 1500,
    revenue: 75000
  }
];

// Initialize the knowledge base
loadKnowledgeBaseFiles();

export async function searchKnowledgeBase(query: string): Promise<{
  text: string;
  visualData?: any;
  tableData?: {
    headers: string[];
    rows: any[][];
    caption?: string;
  };
}> {
  if (cachedData.length === 0) {
    return {
      text: "No data available in the knowledge base.",
    };
  }

  const searchTerms = query.toLowerCase().split(' ');
  
  const relevantEntries = cachedData.filter(entry => {
    const content = entry.content.toLowerCase();
    return searchTerms.some(term => content.includes(term));
  });

  // Group entries by source
  const entriesBySource = relevantEntries.reduce((acc, entry) => {
    const source = entry.source;
    if (!acc[source]) {
      acc[source] = [];
    }
    acc[source].push(entry);
    return acc;
  }, {} as Record<string, DataEntry[]>);

  // Check if the query is asking for visualization
  const needsVisualization = query.toLowerCase().includes('graph') || 
                           query.toLowerCase().includes('chart') ||
                           query.toLowerCase().includes('plot');

  // Check if the query is asking for a table
  const needsTable = query.toLowerCase().includes('table') ||
                    query.toLowerCase().includes('list') ||
                    query.toLowerCase().includes('show data');

  let visualData;
  let tableData;

  if (needsVisualization && relevantEntries.length > 0) {
    const numericColumns = Object.keys(relevantEntries[0]).filter(key => 
      !isNaN(Number(relevantEntries[0][key])) && 
      key !== 'content' && 
      key !== 'source'
    );

    if (numericColumns.length > 0) {
      const firstNumericColumn = numericColumns[0];
      const labels = relevantEntries.map((d, i) => 
        d.month || d['Product Name'] || d.Date || d.date || d.year || `Item ${i + 1}`
      );
      
      visualData = {
        type: 'line',
        labels,
        datasets: [{
          label: firstNumericColumn,
          data: relevantEntries.map(d => Number(d[firstNumericColumn])),
          borderColor: 'rgb(75, 192, 192)',
          tension: 0.1
        }]
      };
    }
  }

  if (needsTable && relevantEntries.length > 0) {
    const source = relevantEntries[0].source;
    const sourceData = entriesBySource[source];
    const headers = Object.keys(sourceData[0]).filter(key => 
      key !== 'content' && key !== 'source'
    );
    const rows = sourceData.map(entry => 
      headers.map(header => entry[header])
    );

    tableData = {
      headers,
      rows,
      caption: `Data from ${source}`
    };
  }

  return {
    text: Object.entries(entriesBySource)
      .map(([source, entries]) => 
        `Data from ${source}:\n` +
        entries.map(entry => 
          Object.entries(entry)
            .filter(([key]) => key !== 'content' && key !== 'source')
            .map(([key, value]) => `${key}: ${value}`)
            .join('\n')
        ).join('\n\n')
      ).join('\n\n'),
    visualData,
    tableData
  };
}