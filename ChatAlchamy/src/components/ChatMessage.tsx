import React from 'react';
import { User, Bot } from 'lucide-react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`py-8 ${isUser ? 'bg-white' : 'bg-gray-50'}`}>
      <div className="max-w-3xl mx-auto flex gap-6 px-4">
        <div className="w-8 h-8 flex-shrink-0">
          {isUser ? (
            <User className="w-full h-full text-gray-600" />
          ) : (
            <Bot className="w-full h-full text-green-600" />
          )}
        </div>
        <div className="flex-1 space-y-2">
          <p className="font-medium text-sm text-gray-600">
            {isUser ? 'You' : 'Assistant'}
          </p>
          <div className="prose prose-slate">
            {message.content}
          </div>
        </div>
      </div>
    </div>
  );
}