import React, { useState } from 'react';
import { Message } from './types';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { FileUpload } from './components/FileUpload';
import { FlaskRound as Flask, Database, X } from 'lucide-react';
import { clearData, getLoadedFiles, searchKnowledgeBase } from './lib/knowledge';
import { DataTable } from './components/DataTable';

const API_URL = import.meta.env.VITE_API_URL || '';
const generateMessageId = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

interface QueryResponse {
  answer: string;
  supported_claim_rate: number;
  warnings: string[];
  evidence: Array<{
    id: string;
    source: string;
    source_record_id?: string | null;
    source_url?: string | null;
  }>;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Welcome to Chat Alchemy! I can help you analyze data and answer pharmaceutical questions using live online sources. How may I assist you today?',
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTable, setCurrentTable] = useState<any>(null);
  const [loadedFiles, setLoadedFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = (filename: string) => {
    setLoadedFiles(getLoadedFiles());
    setMessages((prev) => [
      ...prev,
      {
        id: generateMessageId(),
        role: 'assistant',
        content: `Successfully loaded ${filename}. You can now ask questions about the data.`,
        timestamp: new Date(),
      },
    ]);
    setError(null);
  };

  const handleUploadError = (errorMessage: string) => setError(errorMessage);

  const handleClearData = () => {
    clearData();
    setLoadedFiles([]);
    setCurrentTable(null);
    setMessages([
      {
        id: generateMessageId(),
        role: 'assistant',
        content: 'Uploaded data has been cleared. You can still ask questions using the live pharmaceutical sources.',
        timestamp: new Date(),
      },
    ]);
  };

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: generateMessageId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    setCurrentTable(null);

    try {
      const uploaded = await searchKnowledgeBase(content);
      if (uploaded.tableData) {
        setCurrentTable(uploaded.tableData);
        setMessages((prev) => [
          ...prev,
          {
            id: generateMessageId(),
            role: 'assistant',
            content: `I found ${uploaded.matchCount} matching record${uploaded.matchCount === 1 ? '' : 's'} in your uploaded data.`,
            timestamp: new Date(),
          },
        ]);
        return;
      }

      const response = await fetch(`${API_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: content, max_results: 20 }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Backend returned HTTP ${response.status}`);
      }

      const data = (await response.json()) as QueryResponse;
      const seen = new Set<string>();
      const provenance = data.evidence
        .filter((item) => {
          const key = `${item.source}:${item.source_record_id || item.id}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .map((item) => ({
          id: item.id,
          source: item.source,
          recordId: item.source_record_id,
          url: item.source_url,
        }));

      const uploadNote = uploaded.matchCount > 0
        ? `\n\nI also found ${uploaded.matchCount} matching record${uploaded.matchCount === 1 ? '' : 's'} in your uploaded data.`
        : '';

      setMessages((prev) => [
        ...prev,
        {
          id: generateMessageId(),
          role: 'assistant',
          content: `${data.answer}${uploadNote}`,
          timestamp: new Date(),
          provenance,
          supportRate: data.supported_claim_rate,
          warnings: data.warnings,
        },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown request error';
      setError(message);
      setMessages((prev) => [
        ...prev,
        {
          id: generateMessageId(),
          role: 'assistant',
          content: 'Sorry, there was an error processing your request. Please try again.',
          timestamp: new Date(),
          warnings: [message],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-b from-purple-50 to-white">
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flask className="h-6 w-6 text-purple-600" />
              <h1 className="text-xl font-semibold text-gray-800">Chat Alchemy</h1>
            </div>
            <div className="flex items-center gap-4">
              <FileUpload onUploadComplete={handleFileUpload} onError={handleUploadError} />
              {loadedFiles.length > 0 && (
                <div className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-gray-500" />
                  <span className="text-sm text-gray-600">{loadedFiles.length} file(s)</span>
                  <button onClick={handleClearData} className="text-red-500 hover:text-red-600 p-1 rounded" aria-label="Clear uploaded data">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {error && <div className="mt-2 text-sm text-red-500 bg-red-50 p-2 rounded">{error}</div>}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {currentTable && (
            <div className="py-4">
              <DataTable headers={currentTable.headers} rows={currentTable.rows} caption={currentTable.caption} />
            </div>
          )}

          {isLoading && (
            <div className="py-4 px-4">
              <div className="flex gap-2 items-center text-sm text-gray-500">
                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce [animation-delay:-.3s]" />
                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce [animation-delay:-.5s]" />
              </div>
            </div>
          )}
        </div>
      </div>

      <ChatInput onSend={handleSendMessage} disabled={isLoading} />
    </div>
  );
}

export default App;
