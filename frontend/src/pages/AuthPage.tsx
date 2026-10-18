import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, User as UserIcon, AlertCircle, ArrowRight, ShieldAlert, KeyRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AuthPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const cleanUser = username.trim().toLowerCase();
      const user = await login(username, password);
      if (user.role === 'ADMIN' || cleanUser === 'admin') {
        navigate('/admin');
      } else {
        navigate('/app');
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-md w-full space-y-6">
        {/* Header Branding */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-slate-900 text-white shadow-sm mb-4">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
            Governed Semantic Cache
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Enterprise AI Policy Assistant — Kaveri Tech Solutions Pvt. Ltd.
          </p>
        </div>

        {/* Main Sign In Card */}
        <div className="bg-white py-7 px-6 sm:px-8 border border-slate-200 rounded-xl shadow-xs">
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-slate-900">Enterprise Sign In</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Enter your credentials to access the system.
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <UserIcon className="w-3.5 h-3.5" />
                </div>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin or user"
                  className="w-full text-xs pl-9 pr-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 bg-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <KeyRound className="w-3.5 h-3.5" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full text-xs pl-9 pr-3 py-2 border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 bg-white"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2 px-4 border border-transparent rounded-md shadow-xs text-xs font-medium text-white bg-slate-900 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 flex items-center justify-center gap-1.5 disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Single Shared Role Credentials Guidance */}
          <div className="mt-5 p-3 bg-slate-50 border border-slate-200/80 rounded-lg text-[11px] text-slate-600 space-y-1.5">
            <div className="font-semibold text-slate-700 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-slate-500" />
              <span>Standard Enterprise Accounts</span>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-200/60">
              <div className="bg-white p-2 rounded border border-slate-200">
                <span className="font-medium text-slate-900 block">Admin Portal</span>
                <span className="text-[10px] text-slate-500 font-mono">admin</span>
                <span className="text-[10px] text-slate-400 block">Routes to Governance</span>
              </div>
              <div className="bg-white p-2 rounded border border-slate-200">
                <span className="font-medium text-slate-900 block">User Assistant</span>
                <span className="text-[10px] text-slate-500 font-mono">user</span>
                <span className="text-[10px] text-slate-400 block">Routes to AI Chat</span>
              </div>
            </div>
          </div>

          {/* Security Guarantee Notice */}
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <Lock className="w-3 h-3 text-slate-400" />
              Argon2/Bcrypt + JWT Protected
            </span>
            <span>Role-Based Access</span>
          </div>
        </div>
      </div>
    </div>
  );
};
