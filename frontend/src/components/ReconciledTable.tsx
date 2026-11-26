"use client";

import React, { useState } from "react";
import { Search, CheckCircle2, ArrowRightLeft, FileText, Download } from "lucide-react";
import { ReconciliationPair } from "@/lib/api";

interface ReconciledTableProps {
  items: ReconciliationPair[];
}

export const ReconciledTable: React.FC<ReconciledTableProps> = ({ items }) => {
  const [search, setSearch] = useState("");

  const filtered = items.filter((item) => {
    const q = search.toLowerCase();
    return (
      (item.nf && item.nf.toLowerCase().includes(q)) ||
      (item.supplier && item.supplier.toLowerCase().includes(q)) ||
      (item.match_notes && item.match_notes.toLowerCase().includes(q))
    );
  });

  const formatMoney = (val: any) => {
    const num = parseFloat(val || 0);
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header & Search */}
      <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <span>Historico de Conciliacoes e Baixas</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold">
              {filtered.length} Pares
            </span>
          </h3>
          <p className="text-xs text-slate-500">
            Lançamentos liquidados com quitação exata de nota fiscal e provisão contábil.
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por NF, Fornecedor..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
            <tr>
              <th className="py-3 px-4">Nota Fiscal</th>
              <th className="py-3 px-4">Fornecedor</th>
              <th className="py-3 px-4">Data Pagto</th>
              <th className="py-3 px-4 text-right">Valor da Nota</th>
              <th className="py-3 px-4 text-right">Valor Quitado</th>
              <th className="py-3 px-4 text-center">Score IA</th>
              <th className="py-3 px-4">Status & Rastreabilidade</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">
                  Nenhum registro encontrado.
                </td>
              </tr>
            ) : (
              filtered.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-slate-900">
                    NF {item.nf || "S/N"}
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-800 max-w-xs truncate" title={item.supplier}>
                    {item.supplier}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">
                    {item.created_at}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-medium text-slate-700">
                    {formatMoney(item.invoice_amount)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-emerald-700">
                    {formatMoney(item.reconciled_amount)}

        {(item as any).invoice_total_matched != null && (
            <div className="mt-2 space-y-1 text-[11px] font-normal text-slate-600">
                <p>
                    Total baixado: {
                        formatMoney((item as any).invoice_total_matched)
                    }
                </p>
                <p>
                    Saldo NF: {
                        formatMoney((item as any).invoice_remaining)
                    }
                </p>
                <p>
                    {(item as any).paid_percentage ?? "-"}% baixado
                </p>
            </div>
        )}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-block px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200/50">
                      {Math.round(item.confidence_score * 100)}%
        <span className="block text-[10px] font-normal">
            Confianca
        </span>
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={
        "inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold " +
        ((item as any).display_status === "Quitado"
            ? "bg-emerald-100 text-emerald-800"
            : "bg-amber-100 text-amber-800")
    }>
                      {(item as any).display_status === "Quitado" && (
        <CheckCircle2 className="w-3 h-3" />
    )}
                      <span>{
        (item as any).display_status || "Status a revisar"
    }</span>
                    </span>
                    <span className="text-[11px] text-slate-400 block truncate max-w-xs mt-0.5">
                      {item.match_notes}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// CONCILIA_V5_REAL_STATUS
