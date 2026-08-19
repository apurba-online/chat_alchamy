export interface ProvenanceItem {
  id: string;
  source: string;
  recordId?: string | null;
  url?: string | null;
}

export interface TableData {
  headers: string[];
  rows: unknown[][];
  caption?: string;
}

export interface ChartData {
  type: 'line' | 'bar' | 'pie';
  labels: string[];
  datasets: Array<{ label: string; data: number[] }>;
  title?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  provenance?: ProvenanceItem[];
  supportRate?: number;
  warnings?: string[];
  tableData?: TableData;
  chartData?: ChartData;
}

export interface Chat {
  id: string;
  name: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  analysisContext?: Record<string, unknown>;
}

export interface SearchDetails {
  totalRecords: number;
  searchTerms: string[];
  conditions: Array<{ field: string; value: string }>;
  requestedColumns: string[];
  availableColumns: string[];
  sources: string[];
}

export interface SearchResult {
  text: string;
  matchCount: number;
  foundInKnowledgeBase: boolean;
  searchDetails: SearchDetails;
  tableData?: TableData;
  chartData?: ChartData;
}

export interface DataEntry {
  [key: string]: unknown;
  content: string;
  source: string;
  sheet?: string;
}

export interface QueryResponse {
  answer: string;
  supported_claim_rate: number;
  warnings: string[];
  evidence: Array<{
    id: string;
    source: string;
    source_record_id?: string | null;
    source_url?: string | null;
  }>;
  table?: TableData | null;
  chart?: ChartData | null;
  plan?: { intent: string };
}
