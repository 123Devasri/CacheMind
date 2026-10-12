import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { ShieldAlert, Server } from 'lucide-react';

export const MainLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex">
      <Sidebar />
      <div className="pl-64 flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-20">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
            <span>Corporate Governance Framework</span>
            <span className="text-slate-300">/</span>
            <span className="text-slate-800 font-semibold">Semantic Policy Guard</span>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-md font-medium">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>FHR Target: 1.0% (Clopper-Pearson)</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-md">
              <Server className="h-3.5 w-3.5 text-slate-500" />
              <span>FAISS FlatIP Local</span>
            </div>
          </div>
        </header>

        <main className="flex-1 p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
