import React, { useEffect, useState } from 'react';
import { getSettings, updateSettings } from '../api/client';
import { SettingsData } from '../types';
import {
  SlidersHorizontal,
  Save,
  CheckCircle,
  Shield,
  Server,
  Key
} from 'lucide-react';

export const Settings: React.FC = () => {
  const [data, setData] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  // Form states
  const [minSim, setMinSim] = useState(0.65);
  const [topK, setTopK] = useState(5);
  const [provider, setProvider] = useState('local_mock');
  const [apiKey, setApiKey] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const res = await getSettings();
      setData(res);
      setMinSim(res.min_cosine_similarity);
      setTopK(res.top_k);
      setProvider(res.fallback_provider);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateSettings({
        min_cosine_similarity: minSim,
        top_k: topK,
        fallback_provider: provider,
        openai_api_key: apiKey ? apiKey : undefined
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      await loadSettings();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        Loading system configuration...
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">System & Pipeline Governance Settings</h2>
        <p className="text-xs text-slate-500 mt-1">
          Adjust retrieval hyperparameters, fallback providers, and security bounds.
        </p>
      </div>

      <form onSubmit={handleSave} className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-6">
        {/* FAISS Settings */}
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
            <Server className="h-4 w-4 text-indigo-600" />
            <span>FAISS Retrieval Hyperparameters</span>
          </h3>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Minimum Cosine Similarity Filter (0.0 to 1.0)
              </label>
              <input
                type="number"
                step="0.05"
                min="0.0"
                max="1.0"
                value={minSim}
                onChange={(e) => setMinSim(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 font-mono"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Candidates below this threshold are immediately rejected prior to classification.
              </p>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Top-K Candidate Retrieval Count
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 font-mono"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Maximum nearest neighbors retrieved from the FAISS vector index.
              </p>
            </div>
          </div>
        </div>

        {/* Fallback Provider Settings */}
        <div className="pt-6 border-t border-slate-100">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
            <Key className="h-4 w-4 text-indigo-600" />
            <span>Fallback LLM Provider</span>
          </h3>

          <div className="space-y-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Active Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white"
              >
                <option value="local_mock">Deterministic Local Mock (Safe, offline, clearly labeled)</option>
                <option value="openai">OpenAI API (GPT-4o-mini)</option>
              </select>
            </div>

            {provider === 'openai' && (
              <div>
                <label className="block font-semibold text-slate-700 mb-1">OpenAI API Key</label>
                <input
                  type="password"
                  placeholder="sk-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none font-mono"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Stored in memory and environment; never exposed back to the client UI.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Action bar */}
        <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
          <div>
            {saved && (
              <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1.5">
                <CheckCircle className="h-4 w-4" />
                Settings saved successfully!
              </span>
            )}
          </div>

          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition cursor-pointer"
          >
            <Save className="h-4 w-4" />
            <span>Save Configuration</span>
          </button>
        </div>
      </form>
    </div>
  );
};
