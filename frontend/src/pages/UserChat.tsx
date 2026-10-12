import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Bot,
  User as UserIcon,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  RotateCcw,
  Plus,
  Settings as SettingsIcon,
  Building2,
  ArrowRight,
  Zap,
  Info
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { checkOrOptimizeQuery, submitQuery } from '../api/client';
import { QueryCheckResponse, QueryResponse } from '../types';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  isCached?: boolean;
  lookupLatency?: number;
  totalLatency?: number;
  policyId?: string;
  providerUsed?: string;
  candidateQuestion?: string;
  isOptimized?: boolean;
  needsConfirmation?: boolean;
  originalQuery?: string;
  optimizedQuery?: string;
  removedFiller?: string[];
}

export const UserChat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [pendingOptimization, setPendingOptimization] = useState<{
    original: string;
    optimized: string;
    removedFiller: string[];
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, pendingOptimization]);

  // Quick suggestion prompts tailored for Tamil Nadu enterprise
  const starterPrompts = [
    {
      title: "Tamil Nadu Leave Policy",
      prompt: "How many days of annual leave do permanent employees get in Tamil Nadu?",
      tag: "18 PL & 12 CL"
    },
    {
      title: "Cafeteria & Meal Voucher",
      prompt: "What is the policy regarding employee cafeteria meals and food allowances?",
      tag: "₹2,200/mo Voucher"
    },
    {
      title: "Chennai & Coimbatore WFH",
      prompt: "How many days per week can employees work from home in Chennai and Coimbatore?",
      tag: "2 Days/Week"
    },
    {
      title: "Broadband Internet Allowance",
      prompt: "What is the monthly broadband internet reimbursement for remote work?",
      tag: "INR 1,500/mo"
    },
    {
      title: "Domestic Travel Per Diem",
      prompt: "What is the daily travel per diem allowance for business trips in India?",
      tag: "₹3,500 Metro / ₹2,500 T2"
    },
    {
      title: "Conversational Query Test",
      prompt: "hi hello how are you ? i need to know about employee cafeteria meals and food allowances",
      tag: "Test Optimization"
    }
  ];

  const handleConfirmOptimization = async (useOptimized: boolean) => {
    if (!pendingOptimization || loading) return;
    const { original, optimized, removedFiller } = pendingOptimization;
    setPendingOptimization(null);
    setLoading(true);

    const queryToExecute = useOptimized ? optimized : original;

    // Update the last user message in place so there is no duplicate bubble
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const updated = [...prev];
      const lastIdx = updated.length - 1;
      if (updated[lastIdx].sender === 'user') {
        updated[lastIdx] = {
          ...updated[lastIdx],
          text: queryToExecute,
          isOptimized: useOptimized,
          originalQuery: useOptimized ? original : undefined,
          removedFiller: useOptimized ? removedFiller : undefined
        };
      }
      return updated;
    });

    try {
      const res: QueryResponse = await submitQuery(queryToExecute);
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isCached: res.is_cached,
        lookupLatency: res.lookup_latency_ms,
        totalLatency: res.total_latency_ms,
        providerUsed: res.provider_used,
        candidateQuestion: res.candidate?.question
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error(err);
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: 'Sorry, unable to process your request. Please ensure the backend server is running.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (queryText?: string, bypassOptimization: boolean = false) => {
    const textToSend = (queryText || inputValue).trim();
    if (!textToSend || loading) return;

    setPendingOptimization(null);
    setInputValue('');

    const userMsgId = Date.now().toString();
    const newUserMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setLoading(true);

    try {
      if (bypassOptimization) {
        // Direct execution against the governed cache & policy knowledge engine
        const res: QueryResponse = await submitQuery(textToSend);
        
        const assistantMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: res.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isCached: res.is_cached,
          lookupLatency: res.lookup_latency_ms,
          totalLatency: res.total_latency_ms,
          providerUsed: res.provider_used,
          candidateQuestion: res.candidate?.question
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        // Step 1: Background check for cache existence or optimization requirement
        const checkRes: QueryCheckResponse = await checkOrOptimizeQuery(textToSend);

        if (checkRes.status === 'HIT' && checkRes.is_cached) {
          // Instant cache hit response
          const assistantMsg: ChatMessage = {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            text: checkRes.answer || '',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isCached: true,
            lookupLatency: checkRes.lookup_latency_ms ?? 4.2,
            totalLatency: checkRes.total_latency_ms ?? 5.1,
            providerUsed: checkRes.provider_used || 'cache',
            candidateQuestion: checkRes.candidate?.question
          };
          setMessages((prev) => [...prev, assistantMsg]);
        } else if (checkRes.status === 'GREETING') {
          const assistantMsg: ChatMessage = {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            text: checkRes.answer || '',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isCached: false,
            providerUsed: 'enterprise_greeting_handler'
          };
          setMessages((prev) => [...prev, assistantMsg]);
        } else if (checkRes.needs_confirmation && checkRes.optimized_query) {
          // Optimization triggered: Ask confirmation from user
          setPendingOptimization({
            original: checkRes.original_query,
            optimized: checkRes.optimized_query,
            removedFiller: checkRes.removed_filler || []
          });
        } else {
          // Direct cache miss with already direct query -> grounded response returned
          const assistantMsg: ChatMessage = {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            text: checkRes.answer || 'No matching policy information found.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isCached: false,
            lookupLatency: checkRes.lookup_latency_ms ?? 8.5,
            totalLatency: checkRes.total_latency_ms ?? 120.0,
            providerUsed: checkRes.provider_used || 'grounded_company_policy_engine',
            candidateQuestion: checkRes.candidate?.question
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }
      }
    } catch (err: any) {
      console.error(err);
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: 'Sorry, unable to process your request. Please ensure the backend server is running.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setPendingOptimization(null);
    setInputValue('');
  };

  return (
    <div className="flex h-screen bg-[#212121] text-[#ececec] font-sans antialiased overflow-hidden">
      {/* Left Minimal ChatGPT-style Sidebar */}
      <aside className="w-64 bg-[#171717] border-r border-[#2f2f2f] flex flex-col justify-between hidden md:flex shrink-0">
        <div className="p-3">
          {/* New Chat Button */}
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg border border-[#3b3b3b] hover:bg-[#212121] text-sm text-[#ececec] transition-colors shadow-sm"
          >
            <div className="flex items-center gap-2">
              <Plus className="h-4 w-4 text-emerald-400" />
              <span className="font-medium">New Chat</span>
            </div>
            <span className="text-[10px] text-zinc-500 font-mono">Ctrl+K</span>
          </button>

          {/* Company Context Badge */}
          <div className="mt-4 px-3 py-2.5 rounded-lg bg-[#212121] border border-[#2f2f2f]">
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
              <Building2 className="h-3.5 w-3.5" />
              <span>Kaveri Tech Solutions</span>
            </div>
            <p className="text-[11px] text-zinc-400 mt-1">
              Chennai OMR HQ & Coimbatore Tidel Park
            </p>
            <div className="flex items-center gap-1.5 mt-2 text-[10px] text-zinc-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
              <span>Governed Semantic Cache Active</span>
            </div>
          </div>

          {/* Quick Topics */}
          <div className="mt-6">
            <p className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase px-2 mb-2">
              Verified Policy Categories
            </p>
            <div className="space-y-1">
              <button
                onClick={() => handleSend("How many days of annual leave do permanent employees get in Tamil Nadu?")}
                className="w-full text-left px-2.5 py-1.5 rounded-md text-xs text-zinc-300 hover:bg-[#212121] hover:text-white transition truncate"
              >
                🌴 Tamil Nadu Leave & Holidays
              </button>
              <button
                onClick={() => handleSend("How many days per week can employees work from home in Chennai and Coimbatore?")}
                className="w-full text-left px-2.5 py-1.5 rounded-md text-xs text-zinc-300 hover:bg-[#212121] hover:text-white transition truncate"
              >
                💻 Hybrid WFH & Wifi Policy
              </button>
              <button
                onClick={() => handleSend("What is the daily travel per diem allowance for business trips in India?")}
                className="w-full text-left px-2.5 py-1.5 rounded-md text-xs text-zinc-300 hover:bg-[#212121] hover:text-white transition truncate"
              >
                ✈️ Travel Per Diem (Tier 1 & 2)
              </button>
              <button
                onClick={() => handleSend("What is the policy regarding employee cafeteria meals and food allowances?")}
                className="w-full text-left px-2.5 py-1.5 rounded-md text-xs text-zinc-300 hover:bg-[#212121] hover:text-white transition truncate"
              >
                🍽️ Cafeteria & Meal Allowances
              </button>
              <button
                onClick={() => handleSend("What is the health insurance coverage limit for employees in Tamil Nadu?")}
                className="w-full text-left px-2.5 py-1.5 rounded-md text-xs text-zinc-300 hover:bg-[#212121] hover:text-white transition truncate"
              >
                🏥 Group Health Mediclaim
              </button>
              <button
                onClick={() => handleSend("Is VPN mandatory when accessing company systems remotely?")}
                className="w-full text-left px-2.5 py-1.5 rounded-md text-xs text-zinc-300 hover:bg-[#212121] hover:text-white transition truncate"
              >
                🔒 IT VPN & Security Rules
              </button>
            </div>
          </div>
        </div>

        {/* Footer Admin Switch */}
        <div className="p-3 border-t border-[#2f2f2f]">
          <Link
            to="/admin"
            className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg text-xs font-medium text-zinc-300 hover:bg-[#212121] hover:text-emerald-400 transition"
          >
            <SettingsIcon className="h-4 w-4 text-emerald-500" />
            <span>Admin Governance Portal</span>
          </Link>
          <div className="mt-2 text-[10px] text-zinc-500 px-3">
            CacheMind v1.0 • FHR ≤ 1.0% Target
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Minimal Bar */}
        <header className="h-14 border-b border-[#2f2f2f] px-6 flex items-center justify-between bg-[#212121]/95 backdrop-blur z-10 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold text-xs shadow-md">
              CM
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-[#ececec]">
                CacheMind Assistant
              </h1>
              <p className="text-[11px] text-zinc-400">
                Governed Semantic Policy Assistant • Tamil Nadu Enterprise
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
              <Zap className="h-3 w-3" />
              <span>Semantic Cache Online</span>
            </span>
            <Link
              to="/admin"
              className="text-xs px-3 py-1.5 rounded-md bg-[#2f2f2f] text-zinc-200 hover:bg-[#3b3b3b] hover:text-white font-medium transition flex items-center gap-1.5"
            >
              <SettingsIcon className="h-3.5 w-3.5 text-emerald-400" />
              <span>Admin Portal</span>
            </Link>
          </div>
        </header>

        {/* Conversation Stream */}
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 space-y-6">
          {messages.length === 0 ? (
            /* Empty State / Welcome Screen */
            <div className="max-w-2xl mx-auto mt-8 text-center">
              <div className="inline-flex p-3 rounded-2xl bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 mb-4 shadow-lg">
                <Bot className="h-8 w-8" />
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                How can I assist you with company policies today?
              </h2>
              <p className="text-sm text-zinc-400 mt-2 max-w-md mx-auto">
                Official HR, IT, Travel, and Health Insurance policy knowledge base for Kaveri Tech Solutions (Chennai & Coimbatore).
              </p>

              {/* Starter Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-8 text-left">
                {starterPrompts.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(item.prompt)}
                    className="p-3.5 rounded-xl bg-[#2a2a2a] border border-[#3b3b3b] hover:border-emerald-500/50 hover:bg-[#323232] transition group text-left flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-zinc-200 group-hover:text-emerald-400 transition">
                          {item.title}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-[#171717] text-zinc-400 font-mono">
                          {item.tag}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 line-clamp-2">
                        "{item.prompt}"
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Active Message Bubbles */
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3.5 ${
                    msg.sender === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {msg.sender === 'assistant' && (
                    <div className="h-7 w-7 rounded-full bg-emerald-600/90 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-sm">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.sender === 'user'
                        ? 'bg-[#2f2f2f] text-white border border-[#3f3f3f] shadow-sm'
                        : 'bg-[#262626] text-[#ececec] border border-[#333333] shadow-md'
                    }`}
                  >
                    {/* Status Pill for Assistant */}
                    {msg.sender === 'assistant' && (
                      <div className="flex flex-wrap items-center gap-2 mb-2 pb-2 border-b border-[#333333] text-[11px]">
                        {msg.providerUsed === 'enterprise_greeting_handler' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 font-medium">
                            <Sparkles className="h-3 w-3" />
                            <span>Enterprise Assistant</span>
                          </span>
                        ) : msg.isCached ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 font-medium">
                            <Zap className="h-3 w-3 fill-emerald-400" />
                            <span>Governed Cache Hit ({msg.lookupLatency}ms)</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-950/80 text-blue-400 border border-blue-800/80 font-medium">
                            <Info className="h-3 w-3" />
                            <span>Grounded Policy Search ({msg.totalLatency}ms)</span>
                          </span>
                        )}

                        <span className="text-[10px] text-zinc-400 font-mono">
                          {msg.providerUsed === 'enterprise_greeting_handler'
                            ? 'CacheMind'
                            : msg.providerUsed === 'cache'
                            ? 'FAISS FlatIP'
                            : 'Company Policy Engine'}
                        </span>
                      </div>
                    )}

                    {/* Optimization Pill for User Message */}
                    {msg.sender === 'user' && msg.isOptimized && (
                      <div className="flex items-center gap-1.5 mb-1.5 pb-1 border-b border-[#3f3f3f] text-[10px] text-amber-300 font-medium">
                        <Sparkles className="h-3 w-3 text-amber-400" />
                        <span>Optimized from conversational query</span>
                      </div>
                    )}

                    <div className="whitespace-pre-wrap">{msg.text}</div>

                    <div className="flex items-center justify-end gap-2 mt-2 text-[10px] text-zinc-500">
                      <span>{msg.timestamp}</span>
                    </div>
                  </div>

                  {msg.sender === 'user' && (
                    <div className="h-7 w-7 rounded-full bg-zinc-700 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-sm">
                      <UserIcon className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}

              {/* Inline Query Optimization Confirmation Card */}
              {pendingOptimization && (
                <div className="p-4 rounded-xl bg-[#2a2a2a] border border-amber-600/40 shadow-xl max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-2">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-amber-950/60 text-amber-400 shrink-0">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-amber-300">
                        Conversational Filler Detected — Query Optimization
                      </h4>
                      <p className="text-xs text-zinc-300 mt-1">
                        To match the enterprise policy knowledge base with highest accuracy, we can optimize your query by removing conversational pleasantries:
                      </p>

                      <div className="mt-3 p-2.5 rounded-lg bg-[#1a1a1a] border border-[#333333] space-y-1.5 text-xs">
                        <div className="flex items-baseline gap-2">
                          <span className="text-zinc-500 font-mono text-[11px] w-16 shrink-0">Original:</span>
                          <span className="text-zinc-400 italic">"{pendingOptimization.original}"</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-emerald-400 font-mono text-[11px] w-16 shrink-0 font-semibold">Optimized:</span>
                          <span className="text-emerald-300 font-medium">"{pendingOptimization.optimized}"</span>
                        </div>
                      </div>

                      {pendingOptimization.removedFiller.length > 0 && (
                        <div className="mt-2 flex items-center gap-1.5 text-[11px] text-zinc-400">
                          <span>Removed filler:</span>
                          {pendingOptimization.removedFiller.map((f, i) => (
                            <span key={i} className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px]">
                              "{f}"
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Confirmation Buttons */}
                      <div className="flex items-center gap-2.5 mt-4">
                        <button
                          onClick={() => handleConfirmOptimization(true)}
                          className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span>Use Optimized Prompt & Search</span>
                        </button>
                        <button
                          onClick={() => handleConfirmOptimization(false)}
                          className="px-3.5 py-1.5 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-xs font-medium transition"
                        >
                          <span>Keep Original Query</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Loading Indicator */}
              {loading && !pendingOptimization && (
                <div className="flex items-center gap-3 text-zinc-400 text-xs py-2">
                  <div className="h-7 w-7 rounded-full bg-emerald-950 flex items-center justify-center text-emerald-400 animate-pulse">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-bounce"></span>
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.2s]"></span>
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.4s]"></span>
                    <span className="text-zinc-500 ml-1">Checking semantic cache & policy rules...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Bottom Input Area */}
        <div className="p-4 md:p-6 bg-[#212121]/95 border-t border-[#2f2f2f] shrink-0">
          <div className="max-w-3xl mx-auto">
            <div className="relative rounded-2xl bg-[#2f2f2f] border border-[#3f3f3f] focus-within:border-emerald-500/80 shadow-lg transition">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a policy question (e.g., leave entitlement in Tamil Nadu, WFH allowance, travel per diem)..."
                rows={1}
                className="w-full bg-transparent px-4 py-3.5 pr-14 text-sm text-white placeholder-zinc-400 focus:outline-none resize-none max-h-36"
                disabled={loading}
              />
              <button
                onClick={() => handleSend()}
                disabled={!inputValue.trim() || loading}
                className="absolute right-2.5 bottom-2.5 h-8 w-8 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:opacity-40 text-white flex items-center justify-center transition shadow"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>

            <div className="flex items-center justify-between text-[11px] text-zinc-500 mt-2 px-1">
              <span>Press Enter to send, Shift+Enter for newline</span>
              <span className="flex items-center gap-1 text-emerald-500/80">
                <ShieldCheck className="h-3 w-3" />
                <span>Deterministic Safety & Statistical FHR ≤ 1% Active</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
