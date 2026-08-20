import { useEffect, useMemo, useState } from 'react';
import type { Chat, Message, QueryResponse, SystemHealth } from './types';
import { ChatHeader } from './components/ChatHeader';
import { ChatInput } from './components/ChatInput';
import { ChatMessage } from './components/ChatMessage';
import { ResearchHome } from './components/ResearchHome';
import { BiomedicalModule } from './components/biomedical/BiomedicalModule';
import { getSystemHealth, queryLive } from './lib/api';
import {
  clearData,
  getCandidateDrugEvidence,
  getLoadedFiles,
  loadBackendData,
  searchKnowledgeBase,
} from './lib/knowledge';
import {
  createNewChat,
  deleteChat,
  generateChatName,
  getAllChats,
  getChatById,
  saveChat,
} from './lib/storage';

type ActiveView = 'home' | 'chat' | 'documents';

const newId = () => crypto.randomUUID();

function responseMessage(data: QueryResponse): Message {
  const seen = new Set<string>();
  const provenance = (data.evidence || [])
    .filter(item => {
      const key = `${item.source}:${item.source_record_id || item.id}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map(item => ({
      id: item.id,
      source: item.source,
      recordId: item.source_record_id,
      url: item.source_url,
    }));

  return {
    id: newId(),
    role: 'assistant',
    content: data.answer,
    timestamp: new Date(),
    supportRate: data.supported_claim_rate,
    warnings: data.warnings,
    tableData: data.table || undefined,
    chartData: data.chart || undefined,
    provenance,
    evidenceCount: data.evidence?.length || 0,
    evidenceRecords: (data.evidence || []).map(item => ({
      id: item.id,
      subject: item.subject,
      predicate: item.predicate,
      value: item.value,
      qualifiers: item.qualifiers,
      source: item.source,
      recordId: item.source_record_id,
      url: item.source_url,
      retrievedAt: item.retrieved_at,
      sourceVersion: item.source_version,
      evidenceType: item.evidence_type,
    })),
    planIntent: data.plan?.intent,
    claims: (data.claims || []).map(claim => ({
      text: claim.text,
      supportIds: claim.support_ids || [],
      supported: Boolean(claim.supported),
    })),
    traces: (data.traces || []).map(trace => ({
      source: trace.source,
      operation: trace.operation,
      ok: trace.ok,
      latencyMs: trace.latency_ms,
      resultCount: trace.result_count,
      error: trace.error,
    })),
    conflicts: (data.conflicts || []).map(conflict => ({
      relation: conflict.relation,
      reason: conflict.reason,
    })),
  };
}

export default function App() {
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>('home');
  const [isLoading, setLoading] = useState(false);
  const [loadedFiles, setLoadedFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [chatRevision, setChatRevision] = useState(0);
  const [darkMode, setDarkMode] = useState(() =>
    localStorage.getItem('theme') === 'dark' ||
    (!localStorage.getItem('theme') && matchMedia('(prefers-color-scheme: dark)').matches),
  );

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  useEffect(() => {
    void loadBackendData()
      .then(() => setLoadedFiles(getLoadedFiles()))
      .catch(() => setError('Could not restore previously uploaded data.'));
    void getSystemHealth()
      .then(result => {
        setHealth(result);
        setHealthError(null);
      })
      .catch(err => {
        setHealth(null);
        setHealthError(err instanceof Error ? err.message : 'System health check failed');
      });
  }, []);

  const chats = useMemo(
    () => getAllChats(),
    [chatRevision, currentChat?.updatedAt, activeView],
  );

  const createChat = (prompt?: string) => {
    const chat = createNewChat();
    chat.messages = [
      {
        id: newId(),
        role: 'assistant',
        content:
          'Welcome to **ChatAlchemy Research Workspace**. Ask a biomedical question, query live evidence, or combine an uploaded dataset with current drug, target, approval, and trial records.',
        timestamp: new Date(),
      },
    ];
    saveChat(chat);
    setChatRevision(value => value + 1);
    setCurrentChat({ ...chat });
    setActiveView('chat');
    setError(null);
    if (prompt) {
      window.setTimeout(
        () => window.dispatchEvent(new CustomEvent('question-click', { detail: { question: prompt } })),
        60,
      );
    }
  };

  const selectChat = (id: string) => {
    const chat = getChatById(id);
    if (!chat) return;
    setCurrentChat({ ...chat });
    setActiveView('chat');
    setError(null);
  };

  const removeChat = (id: string) => {
    deleteChat(id);
    setChatRevision(value => value + 1);
    if (currentChat?.id === id) {
      setCurrentChat(null);
      setActiveView('home');
    }
  };

  const renameCurrent = (id: string, name: string) => {
    setChatRevision(value => value + 1);
    if (currentChat?.id === id) setCurrentChat({ ...currentChat, name, updatedAt: new Date() });
  };

  const fileUploaded = () => {
    setLoadedFiles(getLoadedFiles());
    setError(null);
    if (!currentChat) return;
    const message: Message = {
      id: newId(),
      role: 'assistant',
      content:
        'Dataset ready. You can filter, count, tabulate, chart, or combine candidate drug names with live FDA, trial, and target evidence.',
      timestamp: new Date(),
    };
    const updated = {
      ...currentChat,
      messages: [...currentChat.messages, message],
      updatedAt: new Date(),
    };
    setCurrentChat(updated);
    saveChat(updated);
  };

  const clearUploaded = () => {
    void clearData().then(() => setLoadedFiles([]));
    if (!currentChat) return;
    const message: Message = {
      id: newId(),
      role: 'assistant',
      content: 'Local dataset context has been cleared. Live biomedical sources remain available.',
      timestamp: new Date(),
    };
    const updated = {
      ...currentChat,
      messages: [...currentChat.messages, message],
      updatedAt: new Date(),
    };
    setCurrentChat(updated);
    saveChat(updated);
  };

  const send = async (content: string) => {
    if (!currentChat) return;

    const user: Message = { id: newId(), role: 'user', content, timestamp: new Date() };
    let chat: Chat = {
      ...currentChat,
      messages: [...currentChat.messages, user],
      updatedAt: new Date(),
    };
    if (currentChat.messages.length === 1) chat = { ...chat, name: await generateChatName(content) };
    setCurrentChat(chat);
    saveChat(chat);
    setLoading(true);
    setError(null);

    try {
      const uploaded = await searchKnowledgeBase(content);
      const explicitLocalOutput = Boolean(uploaded.tableData || uploaded.chartData) &&
        !/\b(fda|dailymed|clinical\s*trials?|rxnorm|chembl|pubchem|open\s*targets?|target|approved|approval)\b/i.test(content);

      let assistant: Message;
      if (explicitLocalOutput) {
        assistant = {
          id: newId(),
          role: 'assistant',
          content: `I found **${uploaded.matchCount} matching record${uploaded.matchCount === 1 ? '' : 's'}** in your local dataset.`,
          timestamp: new Date(),
          tableData: uploaded.tableData,
          chartData: uploaded.chartData,
          planIntent: 'local_data',
        };
      } else {
        const conversation = chat.messages.slice(-10).map(message => ({
          role: message.role,
          content: message.content,
        }));
        const userEvidence: unknown[] = await getCandidateDrugEvidence();
        if (uploaded.matchCount > 0 && uploaded.text) {
          userEvidence.push({
            subject: 'uploaded data',
            predicate: 'uploaded_context',
            value: uploaded.text.slice(0, 12_000),
            qualifiers: { match_count: uploaded.matchCount },
          });
        }
        const data = await queryLive(content, conversation, userEvidence);
        assistant = responseMessage(data);
        if (uploaded.matchCount > 0 && !assistant.tableData && !assistant.chartData) {
          assistant.content += `\n\nLocal dataset context: **${uploaded.matchCount} matching record${uploaded.matchCount === 1 ? '' : 's'}** were available to this workflow.`;
        }
      }

      chat = { ...chat, messages: [...chat.messages, assistant], updatedAt: new Date() };
      setCurrentChat(chat);
      saveChat(chat);
      setChatRevision(value => value + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown request error';
      const modelUnavailable = /conversational model is temporarily unavailable/i.test(message);
      const assistant: Message = {
        id: newId(),
        role: 'assistant',
        content: modelUnavailable
          ? 'The conversational explanation model is temporarily unavailable. **Live structured biomedical evidence workflows are still available.** Try a disease-to-gene, target-to-drug, FDA, clinical-trial, RxNorm, PubChem, DailyMed, or Open Targets question.'
          : 'I could not complete that research workflow. I did not replace the failed evidence path with an unsupported biomedical answer.',
        timestamp: new Date(),
        warnings: [message],
      };
      chat = { ...chat, messages: [...chat.messages, assistant], updatedAt: new Date() };
      setCurrentChat(chat);
      saveChat(chat);
      setChatRevision(value => value + 1);
      setError(null);
    } finally {
      setLoading(false);
    }
  };

  const transferFromDocuments = () => {
    const latest = getAllChats()[0];
    if (latest) setCurrentChat({ ...latest });
    setChatRevision(value => value + 1);
    setActiveView('chat');
  };

  const goHome = () => {
    setActiveView('home');
    setError(null);
  };

  const openChat = () => {
    if (currentChat) setActiveView('chat');
    else if (chats[0]) selectChat(chats[0].id);
    else createChat();
  };

  const openDocuments = () => {
    setActiveView('documents');
    setError(null);
  };

  const chatView = () => (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-slate-50 dark:bg-slate-950">
      {error && (
        <div className="mx-auto mt-3 w-[min(94%,980px)] rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300">
          {error}
        </div>
      )}
      <div className="scrollbar-subtle flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-5xl px-3 py-5 sm:px-6">
          {currentChat?.messages.map(message => (
            <ChatMessage key={message.id} message={message} darkMode={darkMode} />
          ))}
          {isLoading && (
            <div className="my-5 flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
              <span className="flex gap-1.5"><span className="h-2 w-2 animate-bounce rounded-full bg-indigo-500" /><span className="h-2 w-2 animate-bounce rounded-full bg-indigo-500 [animation-delay:-.2s]" /><span className="h-2 w-2 animate-bounce rounded-full bg-indigo-500 [animation-delay:-.4s]" /></span>
              Planning and querying evidence…
            </div>
          )}
        </div>
      </div>
      <ChatInput onSend={send} disabled={isLoading} darkMode={darkMode} />
    </div>
  );

  return (
    <div className={`flex h-screen flex-col ${darkMode ? 'dark' : ''}`}>
      <ChatHeader
        chatName={currentChat?.name || 'ChatAlchemy'}
        chatId={currentChat?.id || null}
        loadedFiles={loadedFiles}
        onClearData={clearUploaded}
        onFileUpload={() => fileUploaded()}
        onUploadError={setError}
        onSelectChat={selectChat}
        onNewChat={() => createChat()}
        onDeleteChat={removeChat}
        darkMode={darkMode}
        toggleTheme={() => setDarkMode(value => !value)}
        activeView={activeView}
        onGoHome={goHome}
        onOpenChat={openChat}
        onOpenDocuments={openDocuments}
        onRenameChat={renameCurrent}
        health={health}
      />
      <div className="min-h-0 flex-1 overflow-hidden">
        {activeView === 'home' && (
          <ResearchHome
            health={health}
            healthError={healthError}
            loadedFiles={loadedFiles}
            chats={chats}
            onStartChat={createChat}
            onOpenDocuments={openDocuments}
            onFileUpload={() => fileUploaded()}
            onUploadError={setError}
            onClearData={clearUploaded}
            onSelectChat={selectChat}
          />
        )}
        {activeView === 'chat' && currentChat && chatView()}
        {activeView === 'documents' && (
          <div className="scrollbar-subtle h-full overflow-y-auto">
            <BiomedicalModule onTransferToChat={transferFromDocuments} />
          </div>
        )}
      </div>
    </div>
  );
}
