import React, { useState, useEffect, useRef, useLayoutEffect, useCallback } from 'react';
import { usePipeline } from '../context/PipelineContext';
import { Send, Loader2, ChevronDown, ChevronUp, Check } from 'lucide-react';
import { cn } from '../lib/utils';
import { ScrollArea } from './ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { API_BASE, fetchChatModels, type ChatModelDefinition } from '../api/adapter';

interface ChatSource {
  title?: string;
  type?: string;
  section_id?: string;
  score?: number;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  metadata?: ChatSource[];
  modelStats?: ChatModelStats;
}

interface ChatModelStats {
  provider: string;
  model: string;
  model_attribute: string;
  max_tokens_configured: number;
  finish_reason: string;
  retrieved_context_items: number;
  used_direct_answer_retry: boolean;
  ttft_sec: number;
  total_time_sec: number;
  tokens_per_second: number;
  output_tokens: number;
  output_tokens_estimated: boolean;
  reasoning_tokens_estimated: number;
  visible_chars: number;
  reasoning_chars: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  usage_is_exact: boolean;
}

interface ChatPanelProps {
  onResponseStart?: () => void;
}

const createWelcomeMessage = (
  model: ChatModelDefinition | null | undefined,
): ChatMessage => ({
  role: 'assistant',
  content: `Hello! I am your contract assistant${model ? ` running on ${model.display_name}` : ''}. Ask me anything about this contract.`,
});

const loadInitialMessages = (runId: string | null): ChatMessage[] => {
  if (!runId) return [createWelcomeMessage(null)];
  const stored = localStorage.getItem(`chat_${runId}`);
  if (!stored) return [createWelcomeMessage(null)];
  try {
    return JSON.parse(stored);
  } catch (error) {
    console.error('Failed to parse chat memory', error);
    return [createWelcomeMessage(null)];
  }
};

export const ChatPanel: React.FC<ChatPanelProps> = ({ onResponseStart }) => {
  const { runId, stage } = usePipeline();

  const STAGES = ['UPLOADED', 'EXTRACTED', 'SECTIONS_BUILT', 'GRAPH_READY', 'RISKS_ANALYZED', 'REPORT_READY'];
  const currentStageIndex = STAGES.indexOf(stage);
  const isReady = Boolean(runId && currentStageIndex >= 2);
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadInitialMessages(runId));
  const [inputVal, setInputVal] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [expandedSources, setExpandedSources] = useState<Record<number, boolean>>({});
  const [expandedThinking, setExpandedThinking] = useState<Record<number, boolean>>({});
  const [expandedModelStats, setExpandedModelStats] = useState<Record<number, boolean>>({});
  const [availableModels, setAvailableModels] = useState<ChatModelDefinition[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);
  const pendingScrollRef = useRef(false);

  const getViewport = () =>
    scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]') as HTMLDivElement | null;

  const isNearBottom = (viewport: HTMLDivElement) => {
    const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
    return distanceFromBottom <= 72;
  };

  const scrollToBottom = useCallback(() => {
    const viewport = getViewport();
    if (!viewport) return;
    viewport.scrollTop = viewport.scrollHeight;
  }, []);

  const currentModel = availableModels.find((item) => item.id === selectedModelId) ?? availableModels[0] ?? null;
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modelMenuRef.current && !modelMenuRef.current.contains(event.target as Node)) {
        setIsModelMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!runId || !isReady) return;

    let cancelled = false;
    const storageKey = `chat_model_${runId}`;

    const loadChatModels = async () => {
      try {
        const result = await fetchChatModels();
        if (cancelled) return;

        setAvailableModels(result.models);

        const storedMode = localStorage.getItem(storageKey);
        const fallbackModelId = result.default_model_id ?? result.models[0]?.id ?? null;
        const nextModelId = result.models.some((model) => model.id === storedMode) ? storedMode : fallbackModelId;
        setSelectedModelId(nextModelId);

        setMessages((prev) => {
          if (prev.length === 1 && prev[0].role === 'assistant' && !prev[0].thinking && !prev[0].metadata) {
            const selectedModel = result.models.find((model) => model.id === nextModelId) ?? result.models[0] ?? null;
            return [createWelcomeMessage(selectedModel)];
          }
          return prev;
        });
      } catch (error) {
        console.error('Failed to load chat model options', error);
        if (!cancelled) {
          const fallbackModel: ChatModelDefinition = {
            id: 'default',
            model: 'openai/gpt-oss-20b',
            attribute: 'FAST',
            display_name: 'gpt-oss-20b',
            assistant_name: 'gpt-oss-20b Fast Assistant',
          };
          setAvailableModels([fallbackModel]);
          setSelectedModelId(fallbackModel.id);
        }
      }
    };

    loadChatModels();

    return () => {
      cancelled = true;
    };
  }, [runId, isReady]);

  useEffect(() => {
    if (!runId || !selectedModelId) return;
    localStorage.setItem(`chat_model_${runId}`, selectedModelId);
  }, [selectedModelId, runId]);

  useEffect(() => {
    const viewport = getViewport();
    if (!viewport) return;

    const handleScroll = () => {
      shouldAutoScrollRef.current = isNearBottom(viewport);
    };

    handleScroll();
    viewport.addEventListener('scroll', handleScroll);
    return () => viewport.removeEventListener('scroll', handleScroll);
  }, [runId]);

  useLayoutEffect(() => {
    if (!shouldAutoScrollRef.current && !pendingScrollRef.current) return;

    const rafId = window.requestAnimationFrame(() => {
      scrollToBottom();
      pendingScrollRef.current = false;
    });

    return () => window.cancelAnimationFrame(rafId);
  }, [messages, scrollToBottom, status]);

  const saveMessages = (msgs: ChatMessage[]) => {
    setMessages(msgs);
    if (runId) {
      localStorage.setItem(`chat_${runId}`, JSON.stringify(msgs));
    }
  };

  const handleSend = async () => {
    if (!inputVal.trim() || !isReady || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: inputVal };
    const newMessages = [...messages, userMessage];
    shouldAutoScrollRef.current = true;
    pendingScrollRef.current = true;
    saveMessages(newMessages);
    setInputVal('');
    onResponseStart?.();
    setIsLoading(true);
    setStatus('');

    try {
      const response = await fetch(`${API_BASE}/chat/${runId}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map(m => ({ role: m.role, content: m.content })),
          model_id: currentModel?.id ?? selectedModelId,
        })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');

      const assistantMessage: ChatMessage = { role: 'assistant', content: '' };
      let updatedMessages = [...newMessages, assistantMessage];
      pendingScrollRef.current = true;
      saveMessages(updatedMessages);

      if (reader) {
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // keep the last partial line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                
                if (data.event === 'status') {
                  setStatus(data.data);
                } else if (data.event === 'reasoning') {
                  setStatus('');
                  assistantMessage.thinking = (assistantMessage.thinking || '') + data.data;
                  if (shouldAutoScrollRef.current) {
                    pendingScrollRef.current = true;
                  }
                  updatedMessages = [...newMessages, { ...assistantMessage }];
                  saveMessages(updatedMessages);
                } else if (data.event === 'token') {
                  setStatus('');
                  assistantMessage.content += data.data;
                  if (shouldAutoScrollRef.current) {
                    pendingScrollRef.current = true;
                  }
                  updatedMessages = [...newMessages, { ...assistantMessage }];
                  saveMessages(updatedMessages);
                } else if (data.event === 'metadata') {
                  assistantMessage.metadata = data.data;
                  if (shouldAutoScrollRef.current) {
                    pendingScrollRef.current = true;
                  }
                  updatedMessages = [...newMessages, { ...assistantMessage }];
                  saveMessages(updatedMessages);
                } else if (data.event === 'model_stats') {
                  assistantMessage.modelStats = data.data;
                  if (shouldAutoScrollRef.current) {
                    pendingScrollRef.current = true;
                  }
                  updatedMessages = [...newMessages, { ...assistantMessage }];
                  saveMessages(updatedMessages);
                } else if (data.event === 'done') {
                  setIsLoading(false);
                  setStatus('');
                } else if (data.event === 'error') {
                  console.error('SSE Error:', data.data);
                  assistantMessage.content += `\n[Error: ${data.data}]`;
                  updatedMessages = [...newMessages, { ...assistantMessage }];
                  saveMessages(updatedMessages);
                  setIsLoading(false);
                  setStatus('');
                }
              } catch {
                // Ignore incomplete JSON chunks potentially split incorrectly
              }
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      saveMessages([...newMessages, { role: 'assistant', content: 'Sorry, an error occurred while connecting to the assistant.' }]);
    } finally {
      setIsLoading(false);
      setStatus('');
    }
  };

  return (
    <div className="flex h-full flex-col rounded-none border-0 bg-[linear-gradient(180deg,rgba(248,250,252,0.9),rgba(255,255,255,0.98))]">
      <ScrollArea ref={scrollAreaRef} className="flex-1 px-4 py-5">
        <div className="mx-auto max-w-3xl space-y-3">
          {!messages.length && !status && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white/80 p-4 text-sm text-slate-500 shadow-sm">
              Ask about obligations, termination language, payment terms, or clause relationships once the contract context is ready.
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={cn("flex w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
              <div className={cn(
                "min-w-0",
                msg.role === 'user'
                  ? "ml-auto max-w-[82%] rounded-2xl rounded-br-sm bg-[linear-gradient(135deg,#1d4ed8,#0f172a)] px-3.5 py-2.5 shadow-sm"
                  : "w-full"
              )}>
                {msg.role === 'assistant' && msg.thinking?.trim() && (
                  <div className="pb-2">
                    <button
                      type="button"
                      onClick={() => setExpandedThinking((prev) => ({ ...prev, [i]: !prev[i] }))}
                      className="flex w-full items-center justify-between rounded-xl border border-amber-200 bg-amber-50/80 px-2.5 py-2 text-left transition-colors hover:bg-amber-100/80"
                    >
                      <div>
                        <p className="text-[10.5px] font-bold uppercase tracking-wide text-amber-700">Thinking</p>
                        <p className="mt-0.5 text-[11.5px] font-semibold text-amber-900">
                          Model reasoning
                        </p>
                      </div>
                      {expandedThinking[i] ? (
                        <ChevronUp size={15} className="text-amber-700" />
                      ) : (
                        <ChevronDown size={15} className="text-amber-700" />
                      )}
                    </button>
                    {expandedThinking[i] && (
                      <div className="mt-2 rounded-xl border border-amber-200 bg-amber-50/60 px-3 py-2">
                        <div className="text-[12px] leading-relaxed font-medium text-amber-950 whitespace-pre-wrap">
                          {msg.thinking}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                <div className={cn(
                  "text-[13.5px] leading-snug break-words font-semibold",
                  msg.role === 'user'
                    ? "text-white [&_*]:text-white [&_strong]:text-white [&_em]:text-white"
                    : "text-slate-900 [&_*]:text-slate-900 [&_strong]:text-slate-900 [&_em]:text-slate-700"
                )}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({children}) => <p className="m-0 leading-snug">{children}</p>,
                      ul: ({children}) => <ul className="pl-4 my-0.5 list-disc">{children}</ul>,
                      ol: ({children}) => <ol className="pl-4 my-0.5 list-decimal">{children}</ol>,
                      li: ({children}) => <li className="my-0">{children}</li>,
                      h1: ({children}) => <h1 className="text-sm font-bold mt-1 mb-0.5">{children}</h1>,
                      h2: ({children}) => <h2 className="text-sm font-bold mt-1 mb-0.5">{children}</h2>,
                      h3: ({children}) => <h3 className="text-[13px] font-bold mt-1 mb-0.5">{children}</h3>,
                      code: ({children}) => <code className="rounded bg-black/10 px-1 py-0.5 text-[12px] font-mono">{children}</code>,
                      table: ({children}) => (
                        <div className="my-2 w-full overflow-x-auto rounded-lg border border-slate-300 bg-white shadow-sm">
                          <table className="w-full min-w-[520px] border-collapse text-left text-[12px] leading-relaxed">
                            {children}
                          </table>
                        </div>
                      ),
                      thead: ({children}) => <thead className="bg-slate-100">{children}</thead>,
                      tbody: ({children}) => <tbody className="divide-y divide-slate-200">{children}</tbody>,
                      tr: ({children}) => <tr className="align-top even:bg-slate-50/70">{children}</tr>,
                      th: ({children}) => <th className="border-b border-slate-300 px-3 py-2 font-bold text-slate-900">{children}</th>,
                      td: ({children}) => <td className="px-3 py-2 align-top font-medium text-slate-800">{children}</td>,
                    }}
                  >{msg.content}</ReactMarkdown>
                </div>
                {msg.metadata && msg.metadata.length > 0 && (
                  <div className="mt-3 border-t border-slate-200 pt-2">
                    <button
                      type="button"
                      onClick={() => setExpandedSources((prev) => ({ ...prev, [i]: !prev[i] }))}
                      className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50/70 px-2.5 py-2 text-left transition-colors hover:bg-slate-100/80"
                    >
                      <div>
                        <p className="text-[10.5px] font-bold uppercase tracking-wide text-slate-500">Grounding Sources</p>
                        <p className="mt-0.5 text-[11.5px] font-semibold text-slate-700">
                          Sources ({msg.metadata.length})
                        </p>
                      </div>
                      {expandedSources[i] ? (
                        <ChevronUp size={15} className="text-slate-500" />
                      ) : (
                        <ChevronDown size={15} className="text-slate-500" />
                      )}
                    </button>
                    {expandedSources[i] && (
                      <ul className="mt-2 space-y-1">
                        {msg.metadata.map((src, j: number) => (
                          <li key={j} className="rounded-xl border border-slate-200 bg-slate-50/80 px-2.5 py-2 text-[11.5px] font-semibold text-slate-700">
                            <span>
                              {src.title || (src.type + (src.section_id ? ` §${src.section_id}` : ''))}
                              <span className="ml-1 text-[10.5px] font-normal italic text-slate-500">{Math.round((src.score ?? 0) * 100)}% match</span>
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
                {msg.modelStats && (
                  <div className="mt-3 border-t border-slate-200 pt-2">
                    <button
                      type="button"
                      onClick={() => setExpandedModelStats((prev) => ({ ...prev, [i]: !prev[i] }))}
                      className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50/70 px-2.5 py-2 text-left transition-colors hover:bg-slate-100/80"
                    >
                      <div>
                        <p className="text-[10.5px] font-bold uppercase tracking-wide text-slate-500">Model Stats</p>
                        <p className="mt-0.5 text-[11.5px] font-semibold text-slate-700">
                          {msg.modelStats.model.split('/').slice(-1)[0]} • {msg.modelStats.total_time_sec}s
                        </p>
                      </div>
                      {expandedModelStats[i] ? (
                        <ChevronUp size={15} className="text-slate-500" />
                      ) : (
                        <ChevronDown size={15} className="text-slate-500" />
                      )}
                    </button>
                    {expandedModelStats[i] && (
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        {[
                          ['Model', msg.modelStats.model],
                          ['Profile', msg.modelStats.model_attribute],
                          ['Provider', msg.modelStats.provider],
                          ['Finish', msg.modelStats.finish_reason],
                          ['TTFT', `${msg.modelStats.ttft_sec}s`],
                          ['Total Time', `${msg.modelStats.total_time_sec}s`],
                          ['TPS', `${msg.modelStats.tokens_per_second}`],
                          ['Prompt Tokens', `${msg.modelStats.prompt_tokens}${msg.modelStats.usage_is_exact ? '' : ' est.'}`],
                          ['Completion Tokens', `${msg.modelStats.completion_tokens}${msg.modelStats.usage_is_exact ? '' : ' est.'}`],
                          ['Output Tokens', `${msg.modelStats.output_tokens}${msg.modelStats.output_tokens_estimated ? ' est.' : ''}`],
                          ['Total Tokens', `${msg.modelStats.total_tokens}${msg.modelStats.usage_is_exact ? '' : ' est.'}`],
                          ['Reasoning Tokens', `${msg.modelStats.reasoning_tokens_estimated} est.`],
                          ['Context Items', `${msg.modelStats.retrieved_context_items}`],
                          ['Max Tokens', `${msg.modelStats.max_tokens_configured}`],
                          ['Direct Retry', msg.modelStats.used_direct_answer_retry ? 'Yes' : 'No'],
                        ].map(([label, value]) => (
                          <div key={label} className="rounded-xl border border-slate-200 bg-slate-50/80 px-2.5 py-2">
                            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</p>
                            <p className="mt-1 break-all text-[11.5px] font-semibold text-slate-700">{value}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {status && (
            <div className="flex justify-start">
              <div className="inline-flex items-center gap-2 py-2 text-[13px] text-slate-500">
                <Loader2 size={12} className="animate-spin text-slate-400" />
                <span>{status}</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
      <div className="border-t border-slate-200 bg-white/90 p-3 shrink-0 backdrop-blur">
        <div className="mx-auto mb-3 max-w-3xl">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2 text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              <span className="shrink-0">Assistant:</span>
              <div ref={modelMenuRef} className="relative min-w-0">
                <button
                  type="button"
                  onClick={() => setIsModelMenuOpen((prev) => !prev)}
                  className="inline-flex max-w-[320px] items-center gap-2 rounded-lg border border-slate-200 bg-white px-2 py-1 text-left shadow-sm transition-colors hover:bg-slate-50"
                >
                  {currentModel ? (
                    <>
                      <span className="rounded-full border border-slate-300 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.16em] text-slate-600">
                        {currentModel.attribute}
                      </span>
                      <span className="line-clamp-2 text-[10px] font-semibold normal-case leading-tight tracking-normal text-slate-800 break-all">
                        {currentModel.display_name}
                      </span>
                    </>
                  ) : (
                    <span className="line-clamp-2 text-[10px] font-semibold normal-case leading-tight tracking-normal text-slate-800 break-all">
                      Loading...
                    </span>
                  )}
                  <ChevronDown
                    size={12}
                    className={cn(
                      "shrink-0 text-slate-500 transition-transform duration-200",
                      isModelMenuOpen && "rotate-180"
                    )}
                  />
                </button>

                {isModelMenuOpen && (
                  <div className="absolute bottom-[calc(100%+0.45rem)] left-0 z-30 min-w-[240px] max-w-[320px] rounded-xl border border-slate-700 bg-slate-900 p-1.5 text-left shadow-2xl">
                    <p className="px-2 pb-1.5 text-[10px] font-medium normal-case tracking-normal text-slate-400">
                      Available models
                    </p>
                    <div className="space-y-1">
                      {availableModels.map((model) => (
                        <button
                          key={model.id}
                          type="button"
                          onClick={() => {
                            setSelectedModelId(model.id);
                            setIsModelMenuOpen(false);
                          }}
                          className={cn(
                            "flex w-full items-center justify-between rounded-lg px-2.5 py-2 transition-colors",
                            selectedModelId === model.id
                              ? "bg-slate-700 text-white"
                              : "text-slate-100 hover:bg-slate-800"
                          )}
                        >
                          <div className="min-w-0 flex-1 text-left">
                            <div className="break-all text-[11px] font-semibold leading-tight normal-case tracking-normal">
                              {model.display_name}
                            </div>
                            <div className="mt-1 flex items-center">
                              <span className="rounded-full border border-slate-500/70 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.16em] text-slate-300">
                                {model.attribute}
                              </span>
                            </div>
                          </div>
                          {selectedModelId === model.id && <Check size={14} className="ml-2 shrink-0 text-white" />}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="mx-auto flex max-w-3xl items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 p-2 shadow-[0_18px_36px_-28px_rgba(15,23,42,0.7)]">
          <input
            type="text"
            className="h-10 w-full flex-1 rounded-xl border border-input bg-background px-3 py-2 pr-4 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            placeholder={
              !runId 
                ? "Upload a contract first..." 
                : !isReady 
                  ? "Contract context is still indexing..." 
                  : "Ask about obligations, risk allocation, or linked clauses..."
            }
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            disabled={!isReady || isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!inputVal.trim() || !isReady || isLoading}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
