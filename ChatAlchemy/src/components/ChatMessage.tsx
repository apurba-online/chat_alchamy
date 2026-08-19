import React from 'react';
import { User, FlaskRound as Flask, ExternalLink } from 'lucide-react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const uniqueSources = message.provenance
    ? Array.from(new Map(message.provenance.map((item) => [item.source, item])).values())
    : [];

  return (
    <div className={`py-8 ${isUser ? 'bg-white/50' : 'bg-white/80'}`}>
      <div className="max-w-3xl mx-auto flex gap-6 px-4">
        <div className="w-8 h-8 flex-shrink-0">
          {isUser ? (
            <User className="w-full h-full text-gray-600" />
          ) : (
            <Flask className="w-full h-full text-purple-600" />
          )}
        </div>
        <div className="flex-1 space-y-2 min-w-0">
          <p className="font-medium text-sm text-gray-600">{isUser ? 'You' : 'Chat Alchemy'}</p>
          <div className="prose prose-purple max-w-none whitespace-pre-wrap">{message.content}</div>

          {!isUser && uniqueSources.length > 0 && (
            <div className="pt-1 text-xs text-gray-400 flex flex-wrap items-center gap-x-2 gap-y-1">
              <span>Sources:</span>
              {uniqueSources.map((item, index) => (
                <React.Fragment key={`${item.source}-${item.id}`}>
                  {index > 0 && <span>·</span>}
                  {item.url ? (
                    <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-purple-600">
                      {item.source}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <span>{item.source}</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          )}

          {!isUser && message.warnings && message.warnings.length > 0 && (
            <div className="text-xs text-amber-700">{message.warnings.join(' ')}</div>
          )}
        </div>
      </div>
    </div>
  );
}
