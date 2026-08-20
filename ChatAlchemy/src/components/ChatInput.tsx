import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { CornerDownLeft, Send, Sparkles } from 'lucide-react';

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (message: string) => void;
  disabled?: boolean;
  darkMode?: boolean;
}) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const handler = (event: Event) => {
      setInput((event as CustomEvent).detail.question);
      window.setTimeout(() => textareaRef.current?.focus(), 0);
    };
    window.addEventListener('question-click', handler);
    return () => window.removeEventListener('question-click', handler);
  }, []);

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = `${Math.min(element.scrollHeight, 168)}px`;
  }, [input]);

  const submit = () => {
    const value = input.trim();
    if (!value || disabled) return;
    onSend(value);
    setInput('');
  };

  const handleKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-slate-200/80 bg-slate-50/94 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/94 sm:px-6 sm:pb-4 sm:pt-4">
      <div className="mx-auto max-w-4xl">
        <div className="rounded-2xl border border-slate-200 bg-white shadow-[0_18px_50px_-32px_rgba(15,23,42,0.55)] transition focus-within:border-indigo-300 focus-within:shadow-[0_20px_55px_-30px_rgba(79,70,229,0.22)] focus-within:ring-4 focus-within:ring-indigo-500/5 dark:border-slate-800 dark:bg-slate-900 dark:focus-within:border-indigo-700">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={event => setInput(event.target.value)}
            onKeyDown={handleKey}
            disabled={disabled}
            placeholder="Ask a biomedical research question…"
            className="max-h-40 min-h-[56px] w-full resize-none bg-transparent px-4 py-4 text-[15px] leading-6 text-slate-900 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-60 dark:text-white dark:placeholder:text-slate-500 sm:px-5"
          />
          <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-3 py-2.5 dark:border-slate-800 sm:px-4">
            <div className="flex min-w-0 items-center gap-2 text-[11px] text-slate-400">
              <Sparkles className="h-3.5 w-3.5 shrink-0 text-indigo-400" />
              <span className="hidden truncate sm:inline">Specify the disease, drug, target, phase/status, or source when you want a reproducible evidence query.</span>
              <span className="sm:hidden">Live evidence workspace</span>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="hidden items-center gap-1 text-[10px] text-slate-400 md:flex"><CornerDownLeft className="h-3 w-3" />Enter · Shift+Enter for line break</span>
              <button
                onClick={submit}
                disabled={disabled || !input.trim()}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 dark:disabled:bg-slate-800"
                aria-label="Run research query"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
        <p className="mt-2 px-2 text-center text-[10px] leading-4 text-slate-400">Research use only · Verify consequential findings against the linked primary records.</p>
      </div>
    </div>
  );
}
