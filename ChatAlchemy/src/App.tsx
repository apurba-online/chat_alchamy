import React, { useState, useEffect } from 'react';
import { Message } from './types';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { FileUpload } from './components/FileUpload';
import { FlaskRound as Flask, Database, X } from 'lucide-react';
import { openai } from './lib/openai';
import { searchKnowledgeBase, clearData, getLoadedFiles, loadBackendData } from './lib/knowledge';
import { DataTable } from './components/DataTable';

const generateMessageId = () => `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Welcome to Chat Alchemy! I can help you analyze data and answer questions by combining knowledge from PharmAlchemy with general information. How may I assist you today?',
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTable, setCurrentTable] = useState<any>(null);
  const [loadedFiles, setLoadedFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      const count = await loadBackendData();
      if (count > 0) {
        setLoadedFiles(getLoadedFiles());
      }
    };
    loadData();
  }, []);

  const handleFileUpload = (filename: string) => {
    setLoadedFiles(getLoadedFiles());
    setMessages(prev => [...prev, {
      id: generateMessageId(),
      role: 'assistant',
      content: `Successfully loaded ${filename}. You can now ask questions about the data.`,
      timestamp: new Date(),
    }]);
    setError(null);
  };

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleClearData = () => {
    clearData();
    setLoadedFiles([]);
    setCurrentTable(null);
    setMessages([{
      id: generateMessageId(),
      role: 'assistant',
      content: 'All data has been cleared. Please upload new files to continue.',
      timestamp: new Date(),
    }]);
  };

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: generateMessageId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    setCurrentTable(null);

    try {
      const { text: relevantInfo, foundInKnowledgeBase, tableData } = await searchKnowledgeBase(content);

      let systemPrompt = `You are Chat Alchemy, an AI assistant that combines pharmaceutical knowledge with data analysis.
      
      CRITICAL RESPONSE FORMATTING:
      1. When using information from the PharmAlchemy database (ttd_drug_disease.csv), start your response with "According to PharmAlchemy, "
      2. When providing general knowledge without specific data references, start your response with "Based on my general knowledge, "
      
      Always maintain a helpful and informative tone, explaining complex topics clearly.
      Do not use markdown formatting in your responses.
      
      Current context: ${foundInKnowledgeBase ? 'Using PharmAlchemy database' : 'No specific data source'}`;

      let prompt = content;
      if (foundInKnowledgeBase) {
        prompt = `Using the following data:\n\n${relevantInfo}\n\nQuestion: ${content}\n\nProvide a clear, natural response using the appropriate attribution prefix as specified in the system prompt.`;
      }

      const response = await openai.chat.completions.create({
        model: "gpt-3.5-turbo",
        messages: [
          { role: "system", content: systemPrompt },
          ...messages.slice(-5).map(msg => ({
            role: msg.role as any,
            content: msg.content
          })),
          { role: "user", content: prompt }
        ],
        temperature: 0.7,
      });

      const assistantMessage: Message = {
        id: generateMessageId(),
        role: 'assistant',
        content: response.choices[0]?.message?.content || 'Sorry, I could not generate a response.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      
      if (tableData) {
        setCurrentTable(tableData);
      }
    } catch (error: any) {
      console.error('Error processing request:', error);
      setError(error.message || 'An error occurred while processing your request.');
      
      setMessages(prev => [...prev, {
        id: generateMessageId(),
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
        timestamp: new Date(),
      }]);
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
              <FileUpload
                onUploadComplete={handleFileUpload}
                onError={handleUploadError}
              />
              {loadedFiles.length > 0 && (
                <div className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-gray-500" />
                  <span className="text-sm text-gray-600">
                    {loadedFiles.length} file(s)
                  </span>
                  <button
                    onClick={handleClearData}
                    className="text-red-500 hover:text-red-600 p-1 rounded"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {error && (
            <div className="mt-2 text-sm text-red-500 bg-red-50 p-2 rounded">
              {error}
            </div>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          
          {currentTable && (
            <div className="py-4">
              <DataTable 
                headers={currentTable.headers}
                rows={currentTable.rows}
                caption={currentTable.caption}
              />
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