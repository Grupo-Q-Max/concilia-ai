"use client";

import React, { useState } from "react";
import { Search, Building2, CheckCircle2, AlertCircle } from "lucide-react";

interface SupplierSummaryTableProps {
  items: any[];
}

export const SupplierSummaryTable: React.FC<SupplierSummaryTableProps> = ({ items }) => {
  const [search, setSearch] = useState("");

  const filtered = items.filter((item) =>
    item.supplier && item.supplier.toLowerCase().includes(search.toLowerCase())
  );

  const formatMoney = (val: any) => {
    const num = parseFloat(val || 0);
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-4 space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Building2 className="w-5 h-5 text-blue-600" />
            <span>Resumo Consolidado por Fornecedor</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-bold">
              {filtered.length} Fornecedores
            </span>
          </h3>
          <p className="text-xs text-slate-500">
            Balanço financeiro discriminando total faturado, baixado e saldo pendente por parceiro comercial.
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar fornecedor..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
            <tr>
              <th className="py-3 px-4">Fornecedor</th>
              <th className="py-3 px-4 text-center">Qtd Notas</th>
              <th className="py-3 px-4 text-right">Total Faturado</th>
              <th className="py-3 px-4 text-right">Total Pago</th>
              <th className="py-3 px-4 text-right">Saldo em Aberto</th>
              <th className="py-3 px-4 text-center">Situação</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-400">
                  Nenhum fornecedor encontrado.
                </td>
              </tr>
            ) : (
              filtered.map((item, idx) => {
                const openVal = parseFloat(item.open_balance || 0);
                return (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-bold text-slate-900 max-w-sm truncate" title={item.supplier}>
                      {item.supplier}
                    </td>
                    <td className="py-3 px-4 text-center font-mono text-slate-600">
                      {item.invoices_count || 0}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-slate-700">
                      {formatMoney(item.total_invoiced)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-slate-700">
                      {formatMoney(item.total_paid)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold">
                      <span className={openVal > 0 ? "text-amber-700" : "text-emerald-700"}>
                        {formatMoney(openVal)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {openVal > 0 ? (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800">
                          <AlertCircle className="w-3 h-3" />
                          <span>Pendente</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Quitado</span>
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
