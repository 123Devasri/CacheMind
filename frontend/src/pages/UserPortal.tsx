import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  History,
  Star,
  Activity,
  User as UserIcon,
  LogOut,
  Send,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  ThumbsUp,
  ThumbsDown,
  Flag,
  Copy,
  Check,
  RotateCcw,
  Search,
  Trash2,
  Building2,
  FileText,
  Bookmark,
  ChevronRight,
  Info,
  ExternalLink,
  Plus,
  Zap,
  AlertTriangle
} from 'lucide-react';
import {
  submitUserQuery,
  checkOrOptimizeQuery,
  getUserHistory,
  searchUserHistory,
  deleteUserHistory,
  getUserAnalytics,
  submitUserFeedback,
  getUserFavorites,
  addUserFavorite,
  removeUserFavorite,
  getSuggestedQuestions
} from '../api/client';
import {
  QueryResponse,
  UserHistoryItem,
  UserAnalytics,
  FavoriteItem,
  FeedbackItem
} from '../types';
import { useAuth } from '../context/AuthContext';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  isCached?: boolean;
  decision?: string;
  lookupLatency?: number;
  totalLatency?: number;
  policyId?: string | null;
  policyVersion?: string | null;
  sourceCitation?: string | null;
  sourceDocument?: string | null;
  logId?: string;
  isOptimized?: boolean;
  userRating?: 'helpful' | 'not_helpful' | null;
  isFavorited?: boolean;
  grokInvoked?: boolean;
  tokensUsed?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number } | null;
  validationStatus?: string;
  supportingEvidence?: string[];
}

export const UserPortal: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'chat' | 'history' | 'profile'>('chat');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Conversational filler optimization prompt
  const [pendingOptimization, setPendingOptimization] = useState<{
    original: string;
    optimized: string;
    removedFiller: string[];
  } | null>(null);

  // Report Modal State
  const [reportingMessage, setReportingMessage] = useState<ChatMessage | null>(null);
  const [reportReason, setReportReason] = useState('');
  const [submittingReport, setSubmittingReport] = useState(false);

  // History & Favorites State
  const [historyItems, setHistoryItems] = useState<UserHistoryItem[]>([]);
  const [historySearch, setHistorySearch] = useState('');
  const [favoritesList, setFavoritesList] = useState<FavoriteItem[]>([]);
  const [analyticsData, setAnalyticsData] = useState<UserAnalytics | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<{ id: string; question: string; domain: string }[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pendingOptimization]);

  useEffect(() => {
    // Load initial suggested questions
    getSuggestedQuestions().then(setSuggestedQuestions).catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab]);

  const loadHistory = async () => {
    try {
      const items = await getUserHistory(50);
      setHistoryItems(items);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSearchHistory = async () => {
    if (!historySearch.trim()) {
      return loadHistory();
    }
    try {
      const items = await searchUserHistory(historySearch.trim());
      setHistoryItems(items);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteHistory = async (logId?: string) => {
    try {
      await deleteUserHistory(logId);
      loadHistory();
    } catch (e) {
      console.error(e);
    }
  };

  const loadFavorites = async () => {
    try {
      const favs = await getUserFavorites();
      setFavoritesList(favs);
    } catch (e) {
      console.error(e);
    }
  };

  const loadAnalytics = async () => {
    try {
      const data = await getUserAnalytics();
      setAnalyticsData(data);
    } catch (e) {
      console.error(e);
    }
  };

  // Submit Question Flow
  const handleSendMessage = async (queryText?: string) => {
    const textToSend = (queryText || inputValue).trim();
    if (!textToSend || loading) return;

    setInputValue('');
    setPendingOptimization(null);

    // Push user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      // Step A: Check optimization & greeting
      const checkRes = await checkOrOptimizeQuery(textToSend);

      if (checkRes.needs_confirmation && checkRes.optimized_query) {
        setPendingOptimization({
          original: textToSend,
          optimized: checkRes.optimized_query,
          removedFiller: checkRes.removed_filler || []
        });
        setLoading(false);
        return;
      }

      // Step B: Submit directly
      const resp: QueryResponse = await submitUserQuery(textToSend);
      const assistantMsg: ChatMessage = {
        id: `assist-${Date.now()}`,
        sender: 'assistant',
        text: resp.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isCached: resp.is_cached,
        decision: resp.decision,
        lookupLatency: resp.lookup_latency_ms,
        totalLatency: resp.total_latency_ms,
        policyId: resp.policy_id,
        policyVersion: resp.policy_version,
        sourceCitation: resp.source_citation,
        sourceDocument: resp.source_document,
        logId: resp.log_id,
        userRating: null,
        isFavorited: false,
        grokInvoked: resp.grok_invoked,
        tokensUsed: resp.tokens_used,
        validationStatus: resp.validation_status,
        supportingEvidence: resp.supporting_evidence_references
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errMsg: ChatMessage = {
        id: `assist-err-${Date.now()}`,
        sender: 'assistant',
        text: err?.response?.data?.detail || 'Unable to connect to policy knowledge base. Please try again.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isCached: false,
        decision: 'ERROR'
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimizationChoice = async (useOptimized: boolean) => {
    if (!pendingOptimization) return;
    const targetQuery = useOptimized ? pendingOptimization.optimized : pendingOptimization.original;
    setPendingOptimization(null);
    setLoading(true);

    try {
      const resp: QueryResponse = await submitUserQuery(targetQuery);
      const assistantMsg: ChatMessage = {
        id: `assist-${Date.now()}`,
        sender: 'assistant',
        text: resp.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isCached: resp.is_cached,
        decision: resp.decision,
        lookupLatency: resp.lookup_latency_ms,
        totalLatency: resp.total_latency_ms,
        policyId: resp.policy_id,
        policyVersion: resp.policy_version,
        sourceCitation: resp.source_citation,
        sourceDocument: resp.source_document,
        logId: resp.log_id,
        userRating: null,
        isFavorited: false,
        grokInvoked: resp.grok_invoked,
        tokensUsed: resp.tokens_used,
        validationStatus: resp.validation_status,
        supportingEvidence: resp.supporting_evidence_references
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      // error handling
    } finally {
      setLoading(false);
    }
  };

  const handleRateAnswer = async (msg: ChatMessage, rating: 'helpful' | 'not_helpful') => {
    try {
      await submitUserFeedback({
        log_id: msg.logId,
        query_text: msg.sourceDocument || 'Inquiry',
        answer_text: msg.text,
        rating
      });
      setMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, userRating: rating } : m))
      );
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleFavorite = async (msg: ChatMessage) => {
    try {
      if (msg.isFavorited) {
        // Find in favorites
        const fav = favoritesList.find((f) => f.answer === msg.text);
        if (fav) {
          await removeUserFavorite(fav.id);
          setFavoritesList((prev) => prev.filter((f) => f.id !== fav.id));
        }
        setMessages((prev) =>
          prev.map((m) => (m.id === msg.id ? { ...m, isFavorited: false } : m))
        );
      } else {
        const added = await addUserFavorite({
          query_text: msg.sourceDocument || 'Policy Query',
          answer: msg.text,
          policy_id: msg.policyId,
          policy_version: msg.policyVersion,
          is_cached: msg.isCached
        });
        setFavoritesList((prev) => [added, ...prev]);
        setMessages((prev) =>
          prev.map((m) => (m.id === msg.id ? { ...m, isFavorited: true } : m))
        );
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCopyText = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleReportSubmit = async () => {
    if (!reportingMessage || !reportReason.trim()) return;
    setSubmittingReport(true);
    try {
      await submitUserFeedback({
        log_id: reportingMessage.logId,
        query_text: reportingMessage.sourceDocument || 'Policy Inquiry',
        answer_text: reportingMessage.text,
        rating: 'not_helpful',
        is_reported_incorrect: true,
        report_reason: reportReason.trim()
      });
      setReportingMessage(null);
      setReportReason('');
    } catch (e) {
      console.error(e);
    } finally {
      setSubmittingReport(false);
    }
  };

  return (
    <div className="flex h-screen bg-white text-slate-900 font-sans antialiased overflow-hidden">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-slate-200 bg-slate-50 flex flex-col justify-between shrink-0">
        <div>
          {/* Brand */}
          <div className="p-4 border-b border-slate-200">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center shadow-xs">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <h1 className="text-sm font-semibold tracking-tight text-slate-900 leading-none">
                  CacheMind
                </h1>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Governed Semantic Cache
                </p>
              </div>
            </div>
          </div>

          {/* New Chat Button */}
          <div className="p-3">
            <button
              onClick={() => {
                setMessages([]);
                setPendingOptimization(null);
                setActiveTab('chat');
              }}
              className="w-full text-xs font-medium py-2 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-800 flex items-center justify-center gap-1.5 shadow-xs transition-colors"
            >
              <Plus className="w-3.5 h-3.5 text-slate-600" />
              <span>New Conversation</span>
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="px-2 space-y-0.5 text-xs">
            <button
              onClick={() => setActiveTab('chat')}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md font-medium transition-colors ${
                activeTab === 'chat'
                  ? 'bg-slate-200/70 text-slate-900'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Ask a Question</span>
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md font-medium transition-colors ${
                activeTab === 'history'
                  ? 'bg-slate-200/70 text-slate-900'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <History className="w-4 h-4" />
              <span>My History</span>
            </button>


            <button
              onClick={() => setActiveTab('profile')}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md font-medium transition-colors ${
                activeTab === 'profile'
                  ? 'bg-slate-200/70 text-slate-900'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <UserIcon className="w-4 h-4" />
              <span>Profile</span>
            </button>
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="p-3 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-xs font-semibold text-slate-700 shrink-0">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="truncate">
                <p className="text-xs font-medium text-slate-900 truncate">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-[10px] text-slate-400 capitalize">
                  {user?.department || 'Employee'}
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                logout();
                navigate('/login');
              }}
              title="Sign Out"
              className="text-slate-400 hover:text-slate-700 p-1.5 rounded transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
          {user?.role === 'ADMIN' && (
            <button
              onClick={() => navigate('/admin')}
              className="w-full mt-2 text-[11px] font-medium py-1 px-2 rounded bg-slate-900 text-white hover:bg-slate-800 transition-colors flex items-center justify-center gap-1"
            >
              <span>Switch to Admin Portal</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full bg-white overflow-hidden">
        {/* TAB 1: CHAT WORKSPACE */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            {/* Header */}
            <header className="h-12 border-b border-slate-200 px-6 flex items-center justify-between shrink-0 bg-white">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-800">
                  Enterprise Assistant
                </span>
                <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full border border-slate-200">
                  Tamil Nadu Policies (Kaveri Tech)
                </span>
              </div>
              <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                <span>Deterministic Cache Active</span>
              </div>
            </header>

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-6">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-12">
                  <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-900 flex items-center justify-center mb-4 border border-slate-200">
                    <Sparkles className="w-6 h-6 text-emerald-600" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900">
                    How can I assist you with corporate policies today?
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-md">
                    Ask questions on annual leave, hybrid work, travel allowances, mediclaim, or cafeteria meals. Verified answers are served instantly from the semantic cache.
                  </p>

                  {/* Starter Suggestions */}
                  <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-2 mt-6 text-left">
                    {suggestedQuestions.slice(0, 4).map((sq) => (
                      <button
                        key={sq.id}
                        onClick={() => handleSendMessage(sq.question)}
                        className="text-xs p-3 rounded-lg border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-colors text-slate-700 flex flex-col justify-between"
                      >
                        <span className="font-medium text-slate-800 line-clamp-2">
                          {sq.question}
                        </span>
                        <span className="text-[10px] text-slate-400 mt-2 flex items-center gap-1">
                          <Bookmark className="w-2.5 h-2.5" />
                          {sq.domain} Policy
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      msg.sender === 'user' ? 'items-end' : 'items-start'
                    }`}
                  >
                    <div
                      className={`max-w-2xl rounded-xl p-4 text-xs leading-relaxed ${
                        msg.sender === 'user'
                          ? 'bg-slate-900 text-white'
                          : 'bg-white border border-slate-200 text-slate-850 shadow-xs'
                      }`}
                    >
                      {/* Assistant Header: Hit / Miss / Insufficient Evidence Badge */}
                      {msg.sender === 'assistant' && (
                        <div className="flex flex-wrap items-center justify-between pb-2 mb-2 border-b border-slate-100 gap-2">
                          <div className="flex flex-wrap items-center gap-1.5">
                            {msg.isCached || msg.decision === 'HIT' ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">
                                <Zap className="w-3 h-3 text-emerald-600" />
                                CACHE HIT (0 LLM Calls)
                              </span>
                            ) : msg.decision === 'INSUFFICIENT_EVIDENCE' ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold bg-amber-50 text-amber-700 px-2 py-0.5 rounded border border-amber-200">
                                <AlertTriangle className="w-3 h-3 text-amber-600" />
                                INSUFFICIENT EVIDENCE
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200">
                                <Sparkles className="w-3 h-3 text-blue-600" />
                                CACHE MISS
                              </span>
                            )}

                            {msg.grokInvoked ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-medium bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded border border-purple-200">
                                Grok-2 Grounded
                                {msg.tokensUsed?.total_tokens ? ` (${msg.tokensUsed.total_tokens} tokens)` : ''}
                              </span>
                            ) : msg.isCached ? (
                              <span className="text-[10px] text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-150">
                                Grok Skipped
                              </span>
                            ) : (
                              <span className="text-[10px] text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-150">
                                Document Grounded
                              </span>
                            )}

                            {msg.policyVersion && (
                              <span className="text-[10px] text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-150">
                                v{msg.policyVersion}
                              </span>
                            )}
                          </div>

                          <span className="text-[10px] text-slate-400 flex items-center gap-1 shrink-0">
                            <Clock className="w-3 h-3" />
                            {msg.lookupLatency ? `Lookup: ${msg.lookupLatency.toFixed(1)}ms | ` : ''}
                            {msg.totalLatency?.toFixed(1) || '2.0'} ms
                          </span>
                        </div>
                      )}

                      {/* Message Text */}
                      <div className="whitespace-pre-wrap">{msg.text}</div>

                      {/* Citations if available */}
                      {msg.sender === 'assistant' && msg.sourceCitation && (
                        <div className="mt-3 pt-2.5 border-t border-slate-100 text-[11px] text-slate-500 bg-slate-50/50 p-2 rounded border border-slate-150">
                          <span className="font-semibold text-slate-700 block mb-0.5">
                            Authoritative Source:
                          </span>
                          <span>{msg.sourceCitation}</span>
                        </div>
                      )}

                      {/* Interactive Feedback & Actions Footer */}
                      {msg.sender === 'assistant' && (
                        <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-slate-400 text-xs">
                          {/* Left: Helpful / Not Helpful Feedback */}
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleRateAnswer(msg, 'helpful')}
                              title="Helpful Answer"
                              className={`p-1 rounded hover:bg-slate-100 transition-colors ${
                                msg.userRating === 'helpful' ? 'text-emerald-600 bg-emerald-50' : 'text-slate-400'
                              }`}
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleRateAnswer(msg, 'not_helpful')}
                              title="Not Helpful"
                              className={`p-1 rounded hover:bg-slate-100 transition-colors ${
                                msg.userRating === 'not_helpful' ? 'text-rose-600 bg-rose-50' : 'text-slate-400'
                              }`}
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setReportingMessage(msg)}
                              title="Report Outdated or Incorrect Policy"
                              className="text-[11px] text-slate-400 hover:text-rose-600 flex items-center gap-1 ml-2 transition-colors"
                            >
                              <Flag className="w-3 h-3" />
                              <span>Report</span>
                            </button>
                          </div>

                          {/* Right: Copy */}
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleCopyText(msg.text, msg.id)}
                              title="Copy Answer"
                              className="p-1 rounded hover:bg-slate-100 text-slate-400 transition-colors"
                            >
                              {copiedId === msg.id ? (
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

              {/* Conversational Filler Optimization Card */}
              {pendingOptimization && (
                <div className="max-w-2xl bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs shadow-xs">
                  <div className="flex items-start gap-2.5">
                    <Sparkles className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div className="space-y-2 flex-1">
                      <p className="font-semibold text-amber-900">
                        Conversational Greeting Detected
                      </p>
                      <p className="text-amber-800">
                        We detected casual filler words ({pendingOptimization.removedFiller.join(', ')}). Would you like to optimize your inquiry for maximum cache accuracy?
                      </p>
                      <div className="bg-white p-2.5 rounded border border-amber-200 font-mono text-[11px] text-slate-800">
                        "{pendingOptimization.optimized}"
                      </div>
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={() => handleOptimizationChoice(true)}
                          className="bg-slate-900 text-white font-medium px-3 py-1.5 rounded hover:bg-slate-800 transition-colors"
                        >
                          Use Optimized Query
                        </button>
                        <button
                          onClick={() => handleOptimizationChoice(false)}
                          className="bg-white text-slate-700 font-medium px-3 py-1.5 rounded border border-slate-200 hover:bg-slate-50 transition-colors"
                        >
                          Keep Original
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="p-4 border-t border-slate-200 bg-white">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="max-w-3xl mx-auto flex items-center gap-2"
              >
                <input
                  type="text"
                  value={inputValue}
                  disabled={loading}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Ask a policy question (e.g. Tamil Nadu leave days, hybrid work allowance, per diem...)"
                  className="flex-1 text-xs px-3.5 py-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 bg-white shadow-2xs"
                />
                <button
                  type="submit"
                  disabled={loading || !inputValue.trim()}
                  className="bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-white p-2.5 rounded-lg transition-colors shadow-2xs flex items-center justify-center shrink-0"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>
        )}

        {/* TAB 2: MY HISTORY */}
        {activeTab === 'history' && (
          <div className="flex-1 flex flex-col h-full overflow-hidden p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">
                  Personal Query History
                </h2>
                <p className="text-xs text-slate-500">
                  Search and manage your private policy inquiries. Data is isolated to your account.
                </p>
              </div>
              <button
                onClick={() => handleDeleteHistory()}
                className="text-xs text-rose-600 hover:text-rose-700 font-medium flex items-center gap-1.5 px-3 py-1.5 rounded border border-rose-200 hover:bg-rose-50 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear All History</span>
              </button>
            </div>

            {/* Search Input */}
            <div className="mt-4 flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearchHistory()}
                  placeholder="Search your query history..."
                  className="w-full text-xs pl-8 pr-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>
              <button
                onClick={handleSearchHistory}
                className="text-xs px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-md transition-colors"
              >
                Search
              </button>
            </div>

            {/* History Table */}
            <div className="flex-1 overflow-y-auto mt-4 border border-slate-200 rounded-lg">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <tr>
                    <th className="py-2.5 px-3 font-medium">Question</th>
                    <th className="py-2.5 px-3 font-medium w-28">Decision</th>
                    <th className="py-2.5 px-3 font-medium w-24">Latency</th>
                    <th className="py-2.5 px-3 font-medium w-36">Timestamp</th>
                    <th className="py-2.5 px-3 font-medium w-16 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {historyItems.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-400">
                        No personal history records found.
                      </td>
                    </tr>
                  ) : (
                    historyItems.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-3 px-3">
                          <p className="font-medium text-slate-800">{item.query_text}</p>
                          <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">{item.returned_answer}</p>
                        </td>
                        <td className="py-3 px-3">
                          {item.decision === 'HIT' ? (
                            <span className="text-[10px] font-semibold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">
                              CACHE HIT
                            </span>
                          ) : (
                            <span className="text-[10px] font-semibold bg-amber-50 text-amber-700 px-2 py-0.5 rounded border border-amber-200">
                              FALLBACK
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-slate-500">
                          {item.total_latency_ms.toFixed(1)} ms
                        </td>
                        <td className="py-3 px-3 text-slate-400">
                          {new Date(item.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => handleDeleteHistory(item.id)}
                            className="text-slate-400 hover:text-rose-600 transition-colors p-1"
                            title="Delete Item"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: PROFILE */}
        {activeTab === 'profile' && (
          <div className="flex-1 flex flex-col h-full overflow-hidden p-6 max-w-xl">
            <div className="pb-4 border-b border-slate-200 mb-6">
              <h2 className="text-sm font-semibold text-slate-900">
                User Profile
              </h2>
              <p className="text-xs text-slate-500">
                Your authenticated account and role details.
              </p>
            </div>

            <div className="bg-slate-50 p-6 rounded-xl border border-slate-200 space-y-4 text-xs">
              <div className="flex items-center justify-between py-2 border-b border-slate-200">
                <span className="text-slate-500">Full Name</span>
                <span className="font-semibold text-slate-800">{user?.full_name || 'N/A'}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-200">
                <span className="text-slate-500">Username</span>
                <span className="font-mono text-slate-800">{user?.username}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-200">
                <span className="text-slate-500">Email</span>
                <span className="text-slate-800">{user?.email}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-200">
                <span className="text-slate-500">Department</span>
                <span className="text-slate-800">{user?.department || 'General'}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-200">
                <span className="text-slate-500">Role</span>
                <span className="font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  {user?.role}
                </span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-slate-500">Member Since</span>
                <span className="text-slate-800">{user ? new Date(user.created_at).toLocaleDateString() : ''}</span>
              </div>
            </div>

            <button
              onClick={() => {
                logout();
                navigate('/login');
              }}
              className="mt-6 py-2 px-4 text-xs font-medium text-rose-600 bg-rose-50 border border-rose-200 hover:bg-rose-100 rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        )}
      </main>

      {/* REPORT OUTDATED POLICY MODAL */}
      {reportingMessage && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl border border-slate-200 max-w-md w-full p-6 shadow-xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <Flag className="w-4 h-4 text-rose-600" />
                <span>Report Outdated or Incorrect Policy</span>
              </h3>
              <button
                onClick={() => setReportingMessage(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <p className="text-slate-600">
              Please describe the issue with this answer so compliance administrators can review and update authoritative policies.
            </p>

            <div className="bg-slate-50 p-2.5 rounded border border-slate-200 text-slate-700 line-clamp-3">
              "{reportingMessage.text}"
            </div>

            <textarea
              rows={3}
              value={reportReason}
              onChange={(e) => setReportReason(e.target.value)}
              placeholder="e.g. This policy limit was revised last month to INR 2,500..."
              className="w-full text-xs p-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-slate-900"
            />

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setReportingMessage(null)}
                className="px-3 py-1.5 border border-slate-200 rounded-md text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingReport || !reportReason.trim()}
                onClick={handleReportSubmit}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-md transition-colors disabled:opacity-50"
              >
                {submittingReport ? 'Submitting...' : 'Submit Report'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
