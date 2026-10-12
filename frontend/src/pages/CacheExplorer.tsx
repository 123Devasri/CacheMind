import React, { useEffect, useState } from 'react';
import { getCacheEntries, rebuildCacheIndex, createCacheEntry, deleteCacheEntry } from '../api/client';
import { CacheEntry } from '../types';
import {
  Database,
  RefreshCw,
  Plus,
  Trash2,
  CheckCircle,
  Filter,
  Search,
  Check
} from 'lucide-react';

export const CacheExplorer: React.FC = () => {
  const [entries, setEntries] = useState<CacheEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [domainFilter, setDomainFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [rebuilding, setRebuilding] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);

  // New entry form state
  const [newQ, setNewQ] = useState('');
  const [newA, setNewA] = useState('');
  const [newPolicyId, setNewPolicyId] = useState('HR-LEAVE-01');
  const [newDomain, setNewDomain] = useState('HR');

  useEffect(() => {
    loadEntries();
  }, [domainFilter]);

  const loadEntries = async () => {
    try {
      setLoading(true);
      const res = await getCacheEntries(domainFilter || undefined);
      setEntries(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRebuildIndex = async () => {
    try {
      setRebuilding(true);
      await rebuildCacheIndex();
      await loadEntries();
    } catch (err) {
      console.error(err);
    } finally {
      setRebuilding(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Deactivate this cached policy answer?')) {
      await deleteCacheEntry(id);
      await loadEntries();
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQ.trim() || !newA.trim()) return;

    try {
      await createCacheEntry({
        question: newQ,
        answer: newA,
        policy_id: newPolicyId,
        domain: newDomain,
        is_verified: true
      });
      setShowAddModal(false);
      setNewQ('');
      setNewA('');
      await loadEntries();
    } catch (err) {
      console.error(err);
    }
  };

  const filtered = entries.filter((e) =>
    e.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Verified Cache Explorer</h2>
          <p className="text-xs text-slate-500 mt-1">
            Browse and manage verified policy answer records indexed into FAISS.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRebuildIndex}
            disabled={rebuilding}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg border border-slate-200 shadow-2xs transition cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
            <span>{rebuilding ? 'Rebuilding...' : 'Rebuild FAISS Index'}</span>
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Verified Entry</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search questions or answers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
          />
        </div>

        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-slate-400" />
          <select
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-white text-slate-700 focus:outline-none"
          >
            <option value="">All Policy Domains</option>
            <option value="HR">HR Policies</option>
            <option value="IT">IT Security</option>
            <option value="FINANCE">Finance</option>
          </select>
        </div>
      </div>

      {/* Table of Entries */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
              <th className="py-3 px-4">FAISS ID</th>
              <th className="py-3 px-4">Policy & Domain</th>
              <th className="py-3 px-4">Question & Verified Answer</th>
              <th className="py-3 px-4">Conditions</th>
              <th className="py-3 px-4">Hit Count</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/60 transition">
                <td className="py-3.5 px-4 font-mono font-bold text-slate-500">
                  #{item.faiss_id ?? 'N/A'}
                </td>
                <td className="py-3.5 px-4">
                  <span className="font-semibold text-slate-900 block">{item.policy_id}</span>
                  <span className="text-[10px] text-slate-500">{item.domain} · v{item.policy_version}</span>
                </td>
                <td className="py-3.5 px-4 max-w-md">
                  <p className="font-medium text-slate-900">{item.question}</p>
                  <p className="text-slate-500 mt-1 line-clamp-2">{item.answer}</p>
                </td>
                <td className="py-3.5 px-4">
                  <div className="space-y-0.5 text-[11px] text-slate-600">
                    <div>Jurisdiction: <span className="font-medium text-slate-800">{item.jurisdiction}</span></div>
                    <div>Category: <span className="font-medium text-slate-800">{item.employee_category}</span></div>
                  </div>
                </td>
                <td className="py-3.5 px-4 font-mono text-slate-800 font-semibold">
                  {item.hit_count}
                </td>
                <td className="py-3.5 px-4 text-right">
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 rounded transition cursor-pointer"
                    title="Deactivate entry"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal for Adding Verified Entry */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900">Add Verified Cache Entry</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Entries added here are verified and immediately encoded for FAISS similarity matching.
            </p>

            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Standard Question</label>
                <input
                  type="text"
                  required
                  value={newQ}
                  onChange={(e) => setNewQ(e.target.value)}
                  placeholder="e.g. How many annual leave days do permanent employees get?"
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Verified Policy Answer</label>
                <textarea
                  required
                  rows={3}
                  value={newA}
                  onChange={(e) => setNewA(e.target.value)}
                  placeholder="Official authoritative policy clause response..."
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Policy Identifier</label>
                  <input
                    type="text"
                    required
                    value={newPolicyId}
                    onChange={(e) => setNewPolicyId(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Domain</label>
                  <select
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white"
                  >
                    <option value="HR">HR</option>
                    <option value="IT">IT</option>
                    <option value="FINANCE">FINANCE</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow-sm cursor-pointer"
                >
                  Save & Index
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
