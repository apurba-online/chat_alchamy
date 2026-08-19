import type { Chat } from '../types';
import { v4 as uuidv4 } from 'uuid';
import { generateTitle } from './api';

const STORAGE_KEY = 'chat_alchemy_chats_v2';
const MAX_CHATS = 50;
const MAX_MESSAGES_PER_CHAT = 100;

function cleanChat(chat: Chat): Chat {
  return { ...chat, messages: chat.messages.slice(-MAX_MESSAGES_PER_CHAT) };
}

export async function generateChatName(content: string): Promise<string> {
  try { return await generateTitle(content); }
  catch {
    const words = content.match(/[A-Za-z0-9-]+/g)?.filter(x => x.length > 2).slice(0,4) || [];
    return words.map(w => w[0].toUpperCase()+w.slice(1)).join(' ') || 'New Chat';
  }
}

export function saveChat(chat: Chat): void {
  const chats = getAllChats();
  const idx = chats.findIndex(c => c.id === chat.id);
  const value = cleanChat({ ...chat, updatedAt: new Date() });
  if (idx >= 0) chats[idx] = value; else chats.push(value);
  chats.sort((a,b) => b.updatedAt.getTime() - a.updatedAt.getTime());
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(chats.slice(0,MAX_CHATS))); }
  catch {
    const reduced = chats.slice(0,20).map(c => ({...c, messages:c.messages.slice(-20).map(({id,role,content,timestamp})=>({id,role,content,timestamp}))}));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(reduced));
  }
}

export function getAllChats(): Chat[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return (JSON.parse(raw) as any[]).map(chat => ({
      ...chat,
      messages: (chat.messages || []).map((m:any)=>({...m,timestamp:new Date(m.timestamp)})),
      createdAt: new Date(chat.createdAt), updatedAt: new Date(chat.updatedAt),
    })).sort((a,b)=>b.updatedAt.getTime()-a.updatedAt.getTime());
  } catch { return []; }
}

export function getChatById(id:string) { return getAllChats().find(c=>c.id===id); }
export function deleteChat(id:string) { localStorage.setItem(STORAGE_KEY, JSON.stringify(getAllChats().filter(c=>c.id!==id))); }
export function createNewChat(name='New Chat'): Chat {
  const chat: Chat = {id:uuidv4(),name,messages:[],createdAt:new Date(),updatedAt:new Date()};
  saveChat(chat); return chat;
}
export function renameChat(id:string,newName:string) {
  const chats=getAllChats(); const c=chats.find(x=>x.id===id); if(!c)return;
  c.name=newName; c.updatedAt=new Date(); localStorage.setItem(STORAGE_KEY,JSON.stringify(chats));
}
