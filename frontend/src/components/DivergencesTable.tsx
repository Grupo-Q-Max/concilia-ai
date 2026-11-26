"use client";

import React from "react";
import { AlertOctagon, Scale, Check, AlertCircle } from "lucide-react";
import { ReconciliationPair, Transaction } from "@/lib/api";
import { displayNf } from "@/components/SmartSuggestions";

interface DivergencesTableProps {
  divergentPairs: ReconciliationPair[];
  unmappedDebits: Transaction[];
}

export const DivergencesTable: React.FC<DivergencesTableProps> = ({
  divergentPairs,
  unmappedDebits
}) => {
  const formatMoney = (val: any) => {
    const num = parseFloat(val || 0);
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  return (
    <div className="space-y-6">
      {/* 1. Diferenças de Centavos */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-4 space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Scale className="w-5 h-5 text-rose-500" />
              <span>Diferenças Residuais de Centavos (Arredondamento / Descontos)</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 font-bold">
                {divergentPairs.length} Casos
              </span>
            </h3>
            <p className="text-xs text-slate-500">
              Lançamentos associados pela inteligência artificial com divergência mínima (desvio &le; R$ 0,05).
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Nota Fiscal</th>
                <th className="py-3 px-4">Fornecedor</th>
                <th className="py-3 px-4 text-right">Valor da Provisão</th>
                <th className="py-3 px-4 text-right">Valor do Pagamento</th>
                <th className="py-3 px-4 text-right">Diferença Residual</th>
                <th className="py-3 px-4">Justificativa & Auditoria</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {divergentPairs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-400">
                    Nenhuma divergência de centavos encontrada.
                  </td>
                </tr>
              ) : (
                divergentPairs.map((item) => (
                  <tr key={item.id} className="hover:bg-rose-50/20 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      NF {item.nf}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800">
                      {item.supplier}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-slate-700">
                      {formatMoney(item.invoice_amount)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-slate-700">
                      {formatMoney(item.payment_amount)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-rose-600">
                      {parseFloat(item.difference) > 0 ? "+" : ""}
                      {formatMoney(item.difference)}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {item.match_notes}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Pagamentos Sem Provisão */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-4 space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-amber-500" />
              <span>Pagamentos sem Provisão Correspondente (Débitos Não Mapeados)</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-bold">
                {unmappedDebits.length} Itens
              </span>
            </h3>
            <p className="text-xs text-slate-500">
              Pagamentos realizados sem nota de entrada identificada no razão contábil analisado.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Linha</th>
                <th className="py-3 px-4">Data Pagto</th>
                <th className="py-3 px-4">NF Extraída</th>
                <th className="py-3 px-4">Fornecedor</th>
                <th className="py-3 px-4">Histórico Contábil</th>
                <th className="py-3 px-4 text-right">Valor do Pagto</th>
                <th className="py-3 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {unmappedDebits.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-400">
                    Nenhum pagamento sem provisão. Todos os pagamentos foram devidamente conciliados ou compensados!
                  </td>
                </tr>
              ) : (
                unmappedDebits.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-mono text-slate-400">#{item.row_index}</td>
                    <td className="py-3 px-4 font-mono text-slate-600">{item.trans_date}</td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">{displayNf(item.extracted_nf, item.history)}</td>
                    <td className="py-3 px-4 font-medium text-slate-800">{item.extracted_supplier}</td>
                    <td className="py-3 px-4 text-slate-500 max-w-sm truncate">{item.history}</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">{formatMoney(item.amount)}</td>
                    <td className="py-3 px-4 text-center">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-100 text-rose-800">
                        Sem Provisão
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
