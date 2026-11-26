"use client";

import React from "react";
import { 
  Building2, 
  Calendar, 
  FileSpreadsheet, 
  FileText, 
  UploadCloud, 
  CheckCircle2, 
  AlertTriangle,
  Calculator,
  Settings as SettingsIcon
} from "lucide-react";
import { Appearance } from "./Appearance";
import { api } from "@/lib/api";

interface HeaderProps {
  job: any;
  onOpenUpload: () => void;
  onOpenAudit: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({ job, onOpenUpload, onOpenAudit, onOpenSettings }) => {
  return (
    <header className="bg-navy-900 text-white border-b border-navy-800 sticky top-0 z-30 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & System Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center shadow-inner font-extrabold text-xl tracking-wider text-white">
              C
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-white">CONCILIA</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-mono font-semibold border border-blue-400/30">
                  AI
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">Conciliação Contábil Automática & Auditoria</p>
            </div>
          </div>

          {/* Active Job Meta */}
          {job ? (
            <div className="hidden lg:flex items-center space-x-6 text-xs text-slate-300 bg-navy-800/80 px-4 py-2 rounded-lg border border-navy-700">
              <div className="flex items-center space-x-1.5">
                <Building2 className="w-3.5 h-3.5 text-blue-400" />
                <span className="font-medium text-slate-200 truncate max-w-[200px]" title={job.company_name}>
                  {job.company_name}
                </span>
              </div>
              <div className="flex items-center space-x-1.5">
                <Calendar className="w-3.5 h-3.5 text-blue-400" />
                <span>{job.period}</span>
              </div>
              <button 
                onClick={onOpenAudit}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                  job.math_validation_status === "VALID"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20"
                }`}
              >
                <Calculator className="w-3.5 h-3.5" />
                <span>Auditoria: {job.math_validation_status === "VALID" ? "Validada" : "Divergente"}</span>
              </button>
            </div>
          ) : null}

          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <Appearance />
            {job ? (
              <>
                <a
                  href={api.getExcelExportUrl(job.id)}
                  download
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-md transition-shadow shadow-sm hover:shadow"
                  title="Exportar pasta de trabalho Excel com 8 abas analíticas"
                >
                  <FileSpreadsheet className="w-4 h-4" />
                  <span className="hidden sm:inline">Excel 15 Abas</span>
                </a>
                <a
                  href={api.getPdfExportUrl(job.id)}
                  download
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-md transition-shadow border border-slate-600 shadow-sm"
                  title="Exportar Laudo Executivo em PDF"
                >
                  <FileText className="w-4 h-4" />
                  <span className="hidden sm:inline">Laudo PDF</span>
                </a>
              </>
            ) : null}

            <button
              onClick={onOpenSettings}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md transition border border-slate-700 shadow-sm"
              title="Configurar tolerâncias, regras contábeis e IA"
            >
              <SettingsIcon className="w-4 h-4 text-blue-400" />
              <span className="hidden sm:inline">Configurações</span>
            </button>

            <button
              onClick={onOpenUpload}
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-md transition shadow hover:shadow-md"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Importar Razão</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
