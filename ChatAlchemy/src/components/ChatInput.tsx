import { useEffect, useState, type KeyboardEvent } from 'react';
import { Send } from 'lucide-react';
export function ChatInput({onSend,disabled,darkMode=false}:{onSend:(m:string)=>void;disabled?:boolean;darkMode?:boolean}){
  const [input,setInput]=useState('');
  useEffect(()=>{const h=(e:Event)=>setInput((e as CustomEvent).detail.question);window.addEventListener('question-click',h);return()=>window.removeEventListener('question-click',h)},[]);
  const submit=()=>{if(input.trim()&&!disabled){onSend(input.trim());setInput('')}};
  const key=(e:KeyboardEvent)=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submit()}};
  return <div className={`border-t backdrop-blur-sm ${darkMode?'border-gray-700 bg-gray-800/90':'border-gray-200 bg-white/80'}`}><div className="mx-auto max-w-[95%] p-4"><div className="relative"><textarea rows={1} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={key} disabled={disabled} placeholder="Ask about uploaded data, drugs, genes, trials, or biomedical evidence..." className={`w-full resize-none rounded-xl border px-4 py-3 pr-12 text-sm outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 ${darkMode?'border-gray-700 bg-gray-700 text-white':'border-gray-200 bg-white text-gray-900'}`}/><button onClick={submit} disabled={disabled||!input.trim()} className="absolute right-2 top-2.5 rounded-lg p-1.5 text-purple-500 hover:bg-purple-50 disabled:opacity-40 dark:hover:bg-gray-600"><Send className="h-5 w-5"/></button></div><p className="mt-2 text-xs text-gray-500 dark:text-gray-400">ChatAlchemy combines your data with live biomedical evidence and keeps provenance when a live source is used.</p></div></div>;
}
