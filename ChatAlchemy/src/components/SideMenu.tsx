import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Check,
  ChevronLeft,
  Database,
  Edit2,
  FlaskConical,
  Menu,
  MessageSquare,
  Plus,
  Trash2,
} from 'lucide-react';
import type { Chat } from '../types';
import { getAllChats, renameChat } from '../lib/storage';
import { FileUpload } from './FileUpload';

interface SideMenuProps {
  currentChatId: string | null;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onDeleteChat: (id: string) => void;
  onFileUpload: (filename: string) => void;
  onUploadError: (error: string) => void;
  loadedFiles: string[];
  onClearData: () => void;
  darkMode: boolean;
}

export function SideMenu({
  currentChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onFileUpload,
  onUploadError,
  loadedFiles,
  onClearData,
  darkMode,
}: SideMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [chats, setChats] = useState<Chat[]>([]);
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [newChatName, setNewChatName] = useState('');
  const drawerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => setChats(getAllChats()), [currentChatId, isOpen]);
  useEffect(() => { if (editingChatId) inputRef.current?.focus(); }, [editingChatId]);
  useEffect(() => {
    function outside(event: MouseEvent) {
      if (isOpen && drawerRef.current && !drawerRef.current.contains(event.target as Node)) setIsOpen(false);
    }
    function escape(event: KeyboardEvent) { if (isOpen && event.key === 'Escape') setIsOpen(false); }
    if (isOpen) {
      document.addEventListener('mousedown', outside);
      document.addEventListener('keydown', escape);
    }
    return () => {
      document.removeEventListener('mousedown', outside);
      document.removeEventListener('keydown', escape);
    };
  }, [isOpen]);

  const rename = (id: string) => {
    if (newChatName.trim()) {
      renameChat(id, newChatName.trim());
      setChats(getAllChats());
      if (currentChatId === id) onSelectChat(id);
    }
    setEditingChatId(null);
  };

  return <>
    <button onClick={() => setIsOpen(value => !value)} className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white" aria-label="Open research history"><Menu className="h-5 w-5" /></button>
    <AnimatePresence>
      {isOpen && <>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-[1px]" onClick={() => setIsOpen(false)} />
        <motion.div ref={drawerRef} initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }} transition={{ type: 'spring', damping: 28, stiffness: 320 }} className="fixed inset-y-0 left-0 z-50 flex h-screen w-[min(88vw,360px)] flex-col overflow-hidden border-r border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950">
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
            <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white"><FlaskConical className="h-4 w-4" /></span><div><h2 className="text-sm font-semibold text-slate-900 dark:text-white">Research sessions</h2><p className="text-[11px] text-slate-400">Stored in this browser</p></div></div>
            <button onClick={() => setIsOpen(false)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-white" aria-label="Close menu"><ChevronLeft className="h-5 w-5" /></button>
          </div>

          <div className="scrollbar-subtle flex-1 overflow-y-auto p-4">
            <button onClick={() => { onNewChat(); setIsOpen(false); }} className="mb-5 flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-100"><Plus className="h-4 w-4" />New research chat</button>

            <section className="mb-6 rounded-xl border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-slate-900/60">
              <div className="mb-3 flex items-center justify-between gap-2"><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400"><Database className="h-3.5 w-3.5" />Local data</div>{loadedFiles.length > 0 && <button onClick={onClearData} className="text-[11px] font-medium text-rose-600 hover:text-rose-700 dark:text-rose-400">Clear</button>}</div>
              <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">{loadedFiles.length ? `${loadedFiles.length} dataset${loadedFiles.length === 1 ? '' : 's'} available to the workspace` : 'No CSV or Excel datasets loaded'}</p>
              <FileUpload onUploadComplete={onFileUpload} onError={onUploadError} darkMode={darkMode} />
            </section>

            <div className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">History</div>
            {!chats.length ? <div className="rounded-xl border border-dashed border-slate-200 p-4 text-xs leading-5 text-slate-400 dark:border-slate-800">Your research sessions will appear here. Chats stay in this browser unless you export them.</div> : <ul className="space-y-1.5">{chats.map(chat => <li key={chat.id}><div onClick={() => { onSelectChat(chat.id); setIsOpen(false); }} className={`group flex cursor-pointer items-center justify-between gap-2 rounded-xl px-3 py-3 transition ${chat.id === currentChatId ? 'bg-indigo-50 text-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-200' : 'text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900'}`}><div className="flex min-w-0 flex-1 items-center gap-2.5"><MessageSquare className="h-4 w-4 shrink-0 text-slate-400" />{editingChatId === chat.id ? <div className="flex min-w-0 flex-1 items-center gap-1"><input ref={inputRef} value={newChatName} onChange={event => setNewChatName(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') rename(chat.id); else if (event.key === 'Escape') setEditingChatId(null); }} onClick={event => event.stopPropagation()} className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white" /><button onClick={event => { event.stopPropagation(); rename(chat.id); }}><Check className="h-3.5 w-3.5 text-emerald-500" /></button></div> : <span className="truncate text-sm font-medium">{chat.name}</span>}</div>{editingChatId !== chat.id && <div className="flex shrink-0 items-center gap-0.5 opacity-40 transition group-hover:opacity-100"><button onClick={event => { event.stopPropagation(); setEditingChatId(chat.id); setNewChatName(chat.name); }} className="rounded-md p-1 hover:bg-white dark:hover:bg-slate-800"><Edit2 className="h-3.5 w-3.5" /></button><button onClick={event => { event.stopPropagation(); onDeleteChat(chat.id); setChats(getAllChats()); }} className="rounded-md p-1 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30"><Trash2 className="h-3.5 w-3.5" /></button></div>}</div></li>)}</ul>}
          </div>

          <div className="border-t border-slate-200 px-5 py-4 text-[11px] leading-5 text-slate-400 dark:border-slate-800">Research use only · No clinical decision support · Local chat history</div>
        </motion.div>
      </>}
    </AnimatePresence>
  </>;
}
