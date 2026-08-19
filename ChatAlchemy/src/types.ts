export interface ProvenanceItem {
  id: string;
  source: string;
  recordId?: string | null;
  url?: string | null;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  provenance?: ProvenanceItem[];
  supportRate?: number;
  warnings?: string[];
}

export interface Chat {
  messages: Message[];
}
