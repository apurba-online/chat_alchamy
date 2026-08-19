import React, { useState, useRef } from 'react';
import { FlaskRound as Flask, Edit2, Check, Database, X, Sun, Moon, Dna, Home } from 'lucide-react';
import { SideMenu } from './SideMenu';
import { renameChat } from '../lib/storage';

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
  onToggleBiomedical: () => void;
  showBiomedical: boolean;
  onGoHome?: () => void;
  onRenameChat?: (chatId: string, name: string) => void;
}

export function ChatHeader({ chatName, chatId, loadedFiles, onClearData, onFileUpload, onUploadError, onSelectChat, onNewChat, onDeleteChat, darkMode, toggleTheme, onToggleBiomedical, showBiomedical, onGoHome, onRenameChat }: ChatHeaderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(chatName);
  const inputRef = useRef<HTMLInputElement>(null);
  const handleStartEditing = () => { if (!chatId) return; setIsEditing(true); setEditedName(chatName); setTimeout(() => inputRef.current?.focus(), 0); };
  const handleSaveName = () => { if (!chatId || !editedName.trim()) return; renameChat(chatId, editedName.trim()); onRenameChat?.(chatId, editedName.trim()); setIsEditing(false); };
  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === 'Enter') handleSaveName(); else if (e.key === 'Escape') { setIsEditing(false); setEditedName(chatName); } };

  return <header className={`border-b ${darkMode ? 'bg-gray-800/90 border-gray-700' : 'bg-white/80 border-gray-200'} backdrop-blur-sm sticky top-0 z-10`}><div className="max-w-[95%] mx-auto p-4"><div className="flex items-center justify-between"><div className="flex items-center gap-2"><SideMenu currentChatId={chatId} onSelectChat={onSelectChat} onNewChat={onNewChat} onDeleteChat={onDeleteChat} onFileUpload={onFileUpload} onUploadError={onUploadError} loadedFiles={loadedFiles} onClearData={onClearData} darkMode={darkMode}/><div className="flex items-center gap-2"><Flask className={`h-6 w-6 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`}/>{isEditing && chatId ? <div className="flex items-center gap-1"><input ref={inputRef} type="text" value={editedName} onChange={e=>setEditedName(e.target.value)} onKeyDown={handleKeyDown} className={`text-lg font-semibold p-1 rounded ${darkMode?'bg-gray-700 text-white border-gray-600':'bg-white text-gray-800 border-gray-300'} border`}/><button onClick={handleSaveName} className={`p-1 rounded ${darkMode?'hover:bg-gray-700 text-green-400':'hover:bg-gray-200 text-green-600'}`}><Check className="h-4 w-4"/></button></div> : <div className="flex items-center gap-1"><h1 className={`text-xl font-semibold ${darkMode?'text-white':'text-gray-800'}`}>{chatName}</h1>{chatId&&!showBiomedical&&<button onClick={handleStartEditing} className={`p-1 rounded opacity-70 hover:opacity-100 ${darkMode?'hover:bg-gray-700 text-gray-300':'hover:bg-gray-200 text-gray-600'}`}><Edit2 className="h-3 w-3"/></button>}</div>}</div></div><div className="flex items-center gap-4">{onGoHome&&(chatId||showBiomedical)&&<button onClick={onGoHome} className={`p-2 rounded-full ${darkMode?'bg-gray-700 text-gray-300 hover:bg-gray-600':'bg-gray-100 text-gray-600 hover:bg-gray-200'} transition-colors`} aria-label="Go to home"><Home size={18}/></button>}<button onClick={onToggleBiomedical} className={`p-2 rounded-full ${darkMode?'bg-gray-700 text-gray-300 hover:bg-gray-600':'bg-gray-100 text-gray-600 hover:bg-gray-200'} transition-colors`} aria-label={showBiomedical?'Switch to chat':'Switch to biomedical analysis'}><Dna size={18}/></button><button onClick={toggleTheme} className={`p-2 rounded-full ${darkMode?'bg-gray-700 text-gray-300 hover:bg-gray-600':'bg-gray-100 text-gray-600 hover:bg-gray-200'} transition-colors`} aria-label={darkMode?'Switch to light mode':'Switch to dark mode'}>{darkMode?<Sun size={18}/>:<Moon size={18}/>}</button>{loadedFiles.length>0&&!showBiomedical&&<div className="flex items-center gap-2"><Database className={`h-5 w-5 ${darkMode?'text-gray-400':'text-gray-500'}`}/><span className={`text-sm ${darkMode?'text-gray-300':'text-gray-600'}`}>{loadedFiles.length} file(s)</span><button onClick={onClearData} className={`${darkMode?'text-red-400 hover:text-red-300':'text-red-500 hover:text-red-600'} p-1 rounded`}><X className="h-4 w-4"/></button></div>}</div></div></div></header>;
}
