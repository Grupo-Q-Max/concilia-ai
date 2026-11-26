"use client";

import React from "react";
import { 
  LayoutDashboard, 
  CheckCircle2, 
  Clock, 
  AlertOctagon, 
  GitMerge, 
  Users2, 
  History,
  FileCheck,
  Scale
} from "lucide-react";

export type NavTab = 
  | "dashboard" 
  | "composition"
  | "reconciled" 
  | "open" 
  | "divergences" 
  | "manual" 
  | "suppliers" 
  | "history";

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  counts: {
    reconciled: number;
    open: number;
    divergences: number;
    suppliers: number;
  };
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, counts }) => {
  const [collapsed, setCollapsed] = React.useState(false);
  const menuItems = [
    { id: "dashboard", label: "Dashboard Financeiro", icon: LayoutDashboard },
    { id: "composition", label: "Composição Saldo Final", icon: Scale, badge: counts.open + counts.divergences, badgeColor: "bg-blue-100 text-blue-900" },
    { id: "reconciled", label: "Notas Conciliadas", icon: CheckCircle2, badge: counts.reconciled, badgeColor: "bg-emerald-100 text-emerald-800" },
    { id: "open", label: "Notas em Aberto", icon: Clock, badge: counts.open, badgeColor: "bg-amber-100 text-amber-800" },
    { id: "divergences", label: "Divergências & Centavos", icon: AlertOctagon, badge: counts.divergences, badgeColor: "bg-rose-100 text-rose-800" },
    { id: "manual", label: "Conciliação Assistida", icon: GitMerge },
    { id: "suppliers", label: "Resumo por Fornecedor", icon: Users2, badge: counts.suppliers, badgeColor: "bg-slate-100 text-slate-700" },
    { id: "history", label: "Histórico de Arquivos", icon: History },
  ];

  return (
    <aside className={`professional-sidebar ${collapsed ? "is-collapsed" : ""} w-64 bg-white border-r border-slate-200 min-h-[calc(100vh-4rem)] flex flex-col justify-between p-4`}>
      <div className="space-y-1">
        <button className="sidebar-toggle" aria-label={collapsed ? "Expandir menu" : "Recolher menu"} aria-expanded={!collapsed} onClick={() => setCollapsed(!collapsed)}>{collapsed ? "»" : "«"}</button>
        <p className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
          Navegação Principal
        </p>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              title={item.label}
              aria-current={isActive ? "page" : undefined}
              onClick={() => onSelectTab(item.id as NavTab)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-navy-900 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-blue-400" : "text-slate-500"}`} />
                <span className="nav-label">{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 ? (
                <span className={`nav-count text-xs px-2 py-0.5 rounded-full font-mono font-bold ${isActive ? "bg-white/20 text-white" : item.badgeColor}`}>
                  {item.badge}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {/* Engine Status Footer */}
      <div className="sidebar-footer mt-8 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1.5">
        <div className="flex items-center space-x-2 text-emerald-600 font-semibold">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Motor Determinístico Ativo</span>
        </div>
        <p className="text-slate-500 text-[11px] leading-tight">
          Cálculos em Decimal de alta precisão contábil.
        </p>
      </div>
    </aside>
  );
};
