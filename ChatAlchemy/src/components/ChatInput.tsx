import React, { useState, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t bg-white/80 backdrop-blur-sm">
      <div className="max-w-3xl mx-auto p-4">
        <div className="relative">
          <textarea
            rows={1}
            className="w-full resize-none rounded-lg border border-gray-200 bg-white px-4 py-3 pr-12 text-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:opacity-50"
            placeholder="Send a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
          />
          <button
            className="absolute right-2 top-2.5 p-1 rounded-lg hover:bg-purple-50 disabled:opacity-50"
            onClick={handleSubmit}
            disabled={disabled || !input.trim()}
          >
            <Send className="h-5 w-5 text-purple-500" />
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Chat Alchemy combines data analysis with AI to provide comprehensive answers.
        </p>
      </div>
    </div>
  );
}