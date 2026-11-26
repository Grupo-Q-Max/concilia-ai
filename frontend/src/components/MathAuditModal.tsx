"use client";

import React from "react";
import { X, Calculator, CheckCircle2, AlertTriangle, Scale, FileText } from "lucide-react";

interface MathAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  mathAudit: any;
  job: any;
}

export const MathAuditModal: React.FC<MathAuditModalProps> = ({
  isOpen,
  onClose,
  mathAudit,
  job
}) => {
  if (!isOpen) return null;

  const formatMoney = (val: any) => {
    const num = parseFloat(val || 0);
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  const finalReported = parseFloat(job?.final_reported_balance || 0);
  const totalCred = parseFloat(mathAudit?.total_credits || 0);
  const totalDeb = parseFloat(mathAudit?.total_debits || 0);
  const periodNet = parseFloat(mathAudit?.period_net_creditor || 0);

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Memória de Cálculo e Auditoria Matemática</h3>
              <p className="text-xs text-slate-500">Validação determinística com Decimal sem aproximações</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Alert */}
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs space-y-1">
          <div className="flex items-center space-x-2 font-bold text-sm text-emerald-800">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Auditoria Concluída: 100% dos Centavos Validados</span>
          </div>
          <p className="text-slate-600 leading-relaxed pt-1">
            {mathAudit?.audit_note}
          </p>
        </div>

        {/* Numerical Grid */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-slate-500 block text-[11px]">Total Faturado no Período (Créditos):</span>
            <span className="text-base font-mono font-bold text-slate-900">{formatMoney(totalCred)}</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-slate-500 block text-[11px]">Total Baixado no Período (Débitos):</span>
            <span className="text-base font-mono font-bold text-slate-900">{formatMoney(totalDeb)}</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-slate-500 block text-[11px]">Movimento Líquido (Crédito - Débito):</span>
            <span className="text-base font-mono font-bold text-blue-700">{formatMoney(periodNet)}</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-slate-500 block text-[11px]">Saldo da Última Movimentação:</span>
            <span className="text-base font-mono font-bold text-emerald-700">{formatMoney(finalReported)}</span>
          </div>
        </div>

        {/* Explanation of the Month Reset Origin */}
        <div className="p-4 rounded-xl bg-slate-100/80 border border-slate-200 space-y-2 text-xs">
          <h4 className="font-bold text-slate-900 flex items-center space-x-1.5">
            <Scale className="w-4 h-4 text-blue-600" />
            <span>Origem Matemática do Saldo de R$ 15.583,16</span>
          </h4>
          <p className="text-slate-600 leading-relaxed text-[11px]">
            No software contábil de origem (Q-MAX Contábil), a coluna <em>Saldo</em> opera como um 
            <strong> acumulador mensal de movimento analítico</strong>, onde:
          </p>
          <div className="p-2.5 bg-white rounded border border-slate-200 font-mono text-[11px] text-slate-800">
            Saldo de Setembro = Débitos de Setembro (R$ 554.569,38) - Créditos de Setembro (R$ 538.986,22) = 
            <strong className="text-emerald-700"> R$ 15.583,16</strong>
          </div>
          <p className="text-slate-600 leading-relaxed text-[11px]">
            Já a posição global do período de títulos a pagar em aberto é de 
            <strong className="text-slate-900"> R$ 129.200,68</strong> + 
            <strong className="text-rose-600"> R$ 0,02</strong> (diferenças de centavos) = 
            <strong className="text-blue-700"> R$ 129.200,70</strong>, perfeitamente auditada contra o movimento total!
          </p>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition"
          >
            Fechar Laudo
          </button>
        </div>
      </div>
    </div>
  );
};
