import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquareCode,
  Database,
  Cpu,
  GraduationCap,
  SlidersHorizontal,
  PieChart,
  ShieldCheck,
  FileText
} from 'lucide-react';

interface SidebarProps {
  systemReady?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Query Playground', path: '/playground', icon: MessageSquareCode },
    { name: 'Cache Explorer', path: '/cache', icon: Database },
    { name: 'ML Models', path: '/models', icon: Cpu },
    { name: 'Dataset & Training', path: '/training', icon: GraduationCap },
    { name: 'Threshold Safety', path: '/thresholds', icon: ShieldCheck },
    { name: 'Query Clusters', path: '/clusters', icon: PieChart },
    { name: 'Audit Logs', path: '/logs', icon: FileText },
    { name: 'Settings', path: '/settings', icon: SlidersHorizontal },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen fixed left-0 top-0 z-30">
      <div className="p-6 border-b border-slate-800 flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold shadow-md">
          GC
        </div>
        <div>
          <h1 className="text-sm font-semibold text-white tracking-tight">Governed Cache</h1>
          <p className="text-xs text-slate-400">Enterprise AI Security</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white font-semibold'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 bg-slate-950/60">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Policy Guard Active</span>
          </div>
          <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-300 font-mono">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};
