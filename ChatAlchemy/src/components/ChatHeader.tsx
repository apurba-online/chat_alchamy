import { useRef, useState, type KeyboardEvent } from 'react';
import {
  Check,
  Database,
  Edit2,
  FileText,
  FlaskConical,
  Home,
  MessageSquareText,
  Moon,
  Sun,
} from 'lucide-react';
import type { SystemHealth } from '../types';
import { renameChat } from '../lib/storage';
import { SideMenu } from './SideMenu';

type ActiveView = 'home' | 'chat' | 'documents';

interface ChatHeaderProps {
  chatName: string;
  chatId: string | null;
  loadedFiles: string[];
  onClearData: () => void;
  onFileUpload: (filename: string) => void;
  onUploadError: (error: string) => void;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  onDeleteChat: (chatId: string) => void;
  darkMode: boolean;
  toggleTheme: () => void;
  activeView: ActiveView;
  onGoHome: () => void;
  onOpenChat: () => void;
  onOpenDocuments: () => void;
  onRenameChat?: (chatId: string, name: string) => void;
  health: SystemHealth | null;
}

function NavButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Home;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
        active
          ? 'bg-slate-950 text-white shadow-sm dark:bg-white dark:text-slate-950'
          : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white'
      }`}
    >
      <Icon className="h-4 w-4" />
      <span className="hidden lg:inline">{label}</span>
    </button>
  );
}

export function ChatHeader({
  chatName,
  chatId,
  loadedFiles,
  onClearData,
  onFileUpload,
  onUploadError,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  darkMode,
  toggleTheme,
  activeView,
  onGoHome,
  onOpenChat,
  onOpenDocuments,
  onRenameChat,
  health,
}: ChatHeaderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(chatName);
  const inputRef = useRef<HTMLInputElement>(null);

  const startEditing = () => {
    if (!chatId || activeView !== 'chat') return;
    setEditedName(chatName);
    setIsEditing(true);
    window.setTimeout(() => inputRef.current?.focus(), 0);
  };

  const saveName = () => {
    if (!chatId || !editedName.trim()) return;
    const name = editedName.trim();
    renameChat(chatId, name);
    onRenameChat?.(chatId, name);
    setIsEditing(false);
  };

  const handleNameKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') saveName();
    if (event.key === 'Escape') setIsEditing(false);
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/90">
      <div className="mx-auto flex h-16 w-full max-w-[1600px] items-center gap-3 px-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-2">
          <SideMenu
            currentChatId={chatId}
            onSelectChat={onSelectChat}
            onNewChat={onNewChat}
            onDeleteChat={onDeleteChat}
            onFileUpload={onFileUpload}
            onUploadError={onUploadError}
            loadedFiles={loadedFiles}
            onClearData={onClearData}
            darkMode={darkMode}
          />
          <button onClick={onGoHome} className="group flex min-w-0 items-center gap-2.5 rounded-lg px-1 py-1 text-left">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-sm shadow-indigo-500/20">
              <FlaskConical className="h-5 w-5" />
            </span>
            <span className="hidden min-w-0 sm:block">
              <span className="block text-sm font-semibold tracking-tight text-slate-950 dark:text-white">ChatAlchemy</span>
              <span className="block text-[10px] font-medium uppercase tracking-[0.14em] text-slate-400">Evidence workspace</span>
            </span>
          </button>
        </div>

        <nav className="ml-1 flex items-center gap-1 rounded-xl border border-slate-200 bg-slate-50/80 p-1 dark:border-slate-800 dark:bg-slate-900/70">
          <NavButton active={activeView === 'home'} onClick={onGoHome} icon={Home} label="Workspace" />
          <NavButton active={activeView === 'chat'} onClick={onOpenChat} icon={MessageSquareText} label="Research chat" />
          <NavButton active={activeView === 'documents'} onClick={onOpenDocuments} icon={FileText} label="Document lab" />
        </nav>

        <div className="min-w-0 flex-1 px-2 text-center">
          {activeView === 'chat' && chatId && (
            <div className="mx-auto flex max-w-sm items-center justify-center gap-1.5">
              {isEditing ? (
                <>
                  <input
                    ref={inputRef}
                    value={editedName}
                    onChange={event => setEditedName(event.target.value)}
                    onKeyDown={handleNameKey}
                    className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-800 outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                  <button onClick={saveName} className="rounded-md p-1.5 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30" aria-label="Save chat name">
                    <Check className="h-4 w-4" />
                  </button>
                </>
              ) : (
                <>
                  <span className="truncate text-sm font-medium text-slate-600 dark:text-slate-300">{chatName}</span>
                  <button onClick={startEditing} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200" aria-label="Rename chat">
                    <Edit2 className="h-3.5 w-3.5" />
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <div className="hidden items-center gap-2 xl:flex">
            <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1.5 text-xs font-medium ${health?.server_llm_configured ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300' : 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${health?.server_llm_configured ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              {health?.server_llm_configured ? health.model || 'Model ready' : 'Evidence-only mode'}
            </span>
            {loadedFiles.length > 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                <Database className="h-3.5 w-3.5" />{loadedFiles.length}
              </span>
            )}
          </div>
          <button onClick={toggleTheme} className="rounded-lg border border-slate-200 bg-white p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white" aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </header>
  );
}
