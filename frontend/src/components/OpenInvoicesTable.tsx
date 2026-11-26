"use client";

import React, { useState } from "react";
import { Search, Clock, AlertTriangle, Building } from "lucide-react";
import { Transaction } from "@/lib/api";
import { displayNf } from "@/components/SmartSuggestions";

interface OpenInvoicesTableProps {
  items: Transaction[];
}

export const OpenInvoicesTable: React.FC<OpenInvoicesTableProps> = ({ items }) => {
  const [search, setSearch] = useState("");

  const filtered = items.filter((item) => {
    const q = search.toLowerCase();
    const nfVal = displayNf(item.extracted_nf, item.history);
    return (
      (item.extracted_nf && item.extracted_nf.toLowerCase().includes(q)) ||
      (nfVal && nfVal.toLowerCase().includes(q)) ||
      (item.extracted_supplier && item.extracted_supplier.toLowerCase().includes(q)) ||
      (item.history && item.history.toLowerCase().includes(q))
    );
  });

  const formatMoney = (val: any) => {
    const num = parseFloat(val || 0);
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  const totalOpenSum = filtered.reduce((acc, curr) => acc + parseFloat(curr.remaining_amount || "0"), 0);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <span>Notas Fiscais em Aberto (Contas a Pagar)</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold">
              {filtered.length} Títulos
            </span>
          </h3>
          <p className="text-xs text-slate-500">
            Títulos contábeis provisionados no período que não possuem quitação correspondente.
          </p>
        </div>

        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <div className="bg-amber-50 border border-amber-200 px-3.5 py-1.5 rounded-lg text-right">
            <span className="text-[10px] uppercase font-bold text-amber-700 block">Total a Pagar</span>
            <span className="font-mono font-bold text-sm text-amber-900">{formatMoney(totalOpenSum)}</span>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar NF ou Fornecedor..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500"
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
            <tr>
              <th className="py-3 px-4">Linha Razão</th>
              <th className="py-3 px-4">Data Emissão</th>
              <th className="py-3 px-4">Nota Fiscal</th>
              <th className="py-3 px-4">Fornecedor</th>
              <th className="py-3 px-4">Histórico Contábil</th>
              <th className="py-3 px-4 text-right">Valor Original</th>
              <th className="py-3 px-4 text-right">Saldo a Pagar</th>
              <th className="py-3 px-4 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-400">
                  Nenhuma nota em aberto encontrada.
                </td>
              </tr>
            ) : (
              filtered.map((item) => (
                <tr key={item.id} className="hover:bg-amber-50/30 transition-colors">
                  <td className="py-3 px-4 font-mono text-slate-400">
                    #{item.row_index}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">
                    {item.trans_date}
                  </td>
                  <td className="py-3 px-4 font-mono font-bold text-slate-900">
                    NF {displayNf(item.extracted_nf, item.history)}
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-800 max-w-xs truncate" title={item.extracted_supplier}>
                    {item.extracted_supplier}
                  </td>
                  <td className="py-3 px-4 text-slate-500 max-w-md truncate" title={item.history}>
                    {item.history}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-slate-600">
                    {formatMoney(item.amount)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-amber-700">
                    {formatMoney(item.remaining_amount)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800">
                      <Clock className="w-3 h-3" />
                      <span>{
            Number(item.matched_amount || 0) > 0
                ? "Parcial"
                : "Em Aberto"
        }</span>
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

// CONCILIA_V5_OPEN_PARTIAL
