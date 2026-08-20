export interface ProvenanceItem {
  id: string;
  source: string;
  recordId?: string | null;
  url?: string | null;
}

export interface ClaimInfo {
  text: string;
  supportIds: string[];
  supported: boolean;
}

export interface TraceInfo {
  source: string;
  operation: string;
  ok: boolean;
  latencyMs: number;
  resultCount: number;
  error?: string | null;
}

export interface ConflictInfo {
  relation: string;
  reason: string;
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
  claims?: ClaimInfo[];
  traces?: TraceInfo[];
  conflicts?: ConflictInfo[];
  planIntent?: string;
  evidenceCount?: number;
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
  claims?: Array<{
    text: string;
    support_ids: string[];
    supported: boolean;
  }>;
  conflicts?: Array<{
    relation: string;
    reason: string;
  }>;
  traces?: Array<{
    source: string;
    operation: string;
    ok: boolean;
    latency_ms: number;
    result_count: number;
    error?: string | null;
  }>;
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

export interface SystemHealth {
  status: string;
  system: string;
  version?: string;
  local_pharma_database: boolean;
  server_llm_configured: boolean;
  model?: string | null;
  research_use_only?: boolean;
  live_sources?: string[];
  capabilities?: string[];
}
