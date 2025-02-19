import React, { useState } from 'react';
import { Message } from './types';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { MessagesSquare } from 'lucide-react';
import { openai } from './lib/openai';
import { searchKnowledgeBase } from './lib/knowledge';
import { DataVisualization } from './components/DataVisualization';
import { DataTable } from './components/DataTable';

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I can help you analyze your data. You can ask for information, request graphs, or view data in tables.',
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentVisualization, setCurrentVisualization] = useState<any>(null);
  const [currentTable, setCurrentTable] = useState<any>(null);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const { text: relevantInfo, visualData, tableData } = await searchKnowledgeBase(content);

      const systemMessage = relevantInfo 
        ? `You are a helpful assistant. Use the following information to answer the question: ${relevantInfo}`
        : "You are a helpful assistant. If you don't find relevant information in the context, please say that you don't have enough information to answer accurately.";

      const response = await openai.chat.completions.create({
        model: "gpt-3.5-turbo",
        messages: [
          { role: "system", content: systemMessage },
          ...messages.map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          { role: "user", content }
        ],
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.choices[0]?.message?.content || 'Sorry, I could not generate a response.',
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
      
      if (visualData) {
        setCurrentVisualization(visualData);
      }
      
      if (tableData) {
        setCurrentTable(tableData);
      }
    } catch (error) {
      console.error('Error processing request:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="border-b">
        <div className="max-w-3xl mx-auto p-4 flex items-center gap-2">
          <MessagesSquare className="h-6 w-6 text-green-600" />
          <h1 className="text-xl font-semibold text-gray-800">AI Data Assistant</h1>
        </div>
      </header>

      {/* Chat Messages and Visualizations */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          
          {currentVisualization && (
            <DataVisualization 
              data={currentVisualization}
              title="Data Visualization"
            />
          )}
          
          {currentTable && (
            <DataTable 
              headers={currentTable.headers}
              rows={currentTable.rows}
              caption={currentTable.caption}
            />
          )}
          
          {isLoading && (
            <div className="py-4 px-4">
              <div className="flex gap-2 items-center text-sm text-gray-500">
                <div className="w-2 h-2 bg-green-600 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-green-600 rounded-full animate-bounce [animation-delay:-.3s]" />
                <div className="w-2 h-2 bg-green-600 rounded-full animate-bounce [animation-delay:-.5s]" />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Chat Input */}
      <ChatInput onSend={handleSendMessage} disabled={isLoading} />
    </div>
  );
}

export default App;