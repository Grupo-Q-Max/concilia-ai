"use client";

import React from "react";
import { 
  DollarSign, 
  ArrowUpRight, 
  ArrowDownLeft, 
  Scale, 
  CheckCircle, 
  AlertCircle, 
  Clock, 
  TrendingUp,
  FileSpreadsheet,
  Info
} from "lucide-react";

interface DashboardProps {
  summary: any;
  job: any;
  mathAudit: any;
  monthlyEvolution: any[];
  onOpenAudit: () => void;
  onNavigateTab: (tab: any) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  summary,
  job,
  mathAudit,
  monthlyEvolution,
  onOpenAudit,
  onNavigateTab
}) => {

  // CONCILIA_V5_MONTHLY_29E3B

  const formatMonthV5 = (value: string) => {
    if (value === "SEM_DATA") {
      return "Data n\u00e3o identificada";
    }

    const match = /^(\d{4})-(\d{2})$/.exec(value);

    if (!match) return value;

    const year = Number(match[1]);
    const month = Number(match[2]);

    if (month < 1 || month > 12) return value;

    const names = [
      "Janeiro", "Fevereiro", "Mar\u00e7o", "Abril",
      "Maio", "Junho", "Julho", "Agosto",
      "Setembro", "Outubro", "Novembro", "Dezembro"
    ];

    return `${names[month - 1]}/${year}`;
  };

  const validMonthCountV5 = (monthlyEvolution || [])
    .filter((item) => /^\d{4}-\d{2}$/.test(item.month))
    .length;

  const formatMoney = (val: any) => {
    const num = parseFloat(val || 0);
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  const totalCredits = parseFloat(summary?.total_credits_value || 0);
  const totalDebits = parseFloat(summary?.total_debits_value || 0);
  const totalOpen = parseFloat(summary?.total_open_value || 0);
  const totalReconciled = parseFloat(summary?.total_reconciled_value || 0);
  const finalReported = parseFloat(job?.final_reported_balance || 0);
  const initialBalance = parseFloat(job?.initial_balance || 0);
  const periodNet = parseFloat(summary?.period_net_movement || 0);
  const ratePct = summary?.reconciliation_rate_pct || 0;
  

  // CONCILIA_V5_CLOSING_29E4

  const closingV5 = summary?.closing_v5;
  const closingReadyV5 = Boolean(closingV5);
  const closingValidV5 = closingV5?.valid === true;

  const closingMoneyV5 = (value: any) => {
    if (value === undefined || value === null) {
      return "\u2014";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "\u2014";
    }

    const formatted = formatMoney(number);

    return number > 0 ? "+" + formatted : formatted;
  };

  const closingRowsV5 = [
    {
      key: "opening_residual",
      label: "Saldo anterior residual",
      style: "bg-slate-50 border-slate-200 text-slate-800",
    },
    {
      key: "opening_unproven",
      label: "Saldo anterior n\u00e3o comprovado",
      style: "bg-amber-50 border-amber-200 text-amber-900",
    },
    {
      key: "credit_residual",
      label: "Cr\u00e9ditos residuais",
      style: "bg-amber-50 border-amber-200 text-amber-900",
      tab: "open",
    },
    {
      key: "debit_residual",
      label: "D\u00e9bitos residuais",
      style: "bg-purple-50 border-purple-200 text-purple-900",
      tab: "divergences",
    },
    {
      key: "cent_differences",
      label: "Diferen\u00e7as de centavos",
      style: "bg-rose-50 border-rose-200 text-rose-900",
      tab: "divergences",
    },
    {
      key: "other_residual",
      label: "Outros valores a revisar",
      style: "bg-rose-50 border-rose-200 text-rose-900",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner: Mathematical Audit Notice */}
      <div className="bg-gradient-to-r from-navy-900 to-navy-800 rounded-xl p-5 text-white shadow-lg border border-navy-700">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                  closingValidV5
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                    : "bg-amber-500/20 text-amber-300 border-amber-500/30"
                }`}>
                {!closingReadyV5
                  ? "Composi\u00e7\u00e3o indispon\u00edvel"
                  : closingValidV5
                    ? "Composi\u00e7\u00e3o validada"
                    : "Composi\u00e7\u00e3o a revisar"}
              </span>
              <span className="text-xs text-slate-300">
                Saldo Informado no Razão: <strong className="text-white">{formatMoney(finalReported)}</strong>
              </span>
            </div>
            <h2 className="text-lg font-bold tracking-tight text-white">
              {job?.company_name || "Razão Contábil Fornecedores"}
            </h2>
            <p className="text-xs text-slate-300 max-w-3xl leading-relaxed">
              O saldo final da última movimentação ({formatMoney(finalReported)}) foi detectado dinamicamente 
              e comparado com a composição contábil. Posição de títulos em aberto: {formatMoney(totalOpen)}.
            </p>
          </div>
          <button
            onClick={onOpenAudit}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition shadow flex items-center space-x-1.5 whitespace-nowrap"
          >
            <Info className="w-4 h-4" />
            <span>Ver Memória de Cálculo</span>
          </button>
        </div>
      </div>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Faturado */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Faturado (Créditos)</span>
            <span className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <ArrowDownLeft className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-slate-900 tracking-tight">{formatMoney(totalCredits)}</span>
            <p className="text-xs text-slate-500 mt-1">{summary?.total_invoices_count || 0} notas de entrada</p>
          </div>
        </div>

        {/* Total Baixado */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Baixado (Débitos)</span>
            <span className="p-2 bg-slate-100 text-slate-700 rounded-lg">
              <ArrowUpRight className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-slate-900 tracking-tight">{formatMoney(totalDebits)}</span>
            <p className="text-xs text-slate-500 mt-1">{summary?.total_payments_count || 0} pagamentos efetuados</p>
          </div>
        </div>

        {/* Total Conciliado */}
        <div className="bg-white p-5 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-800 uppercase tracking-wider">Total Conciliado</span>
            <span className="p-2 bg-emerald-100 text-emerald-700 rounded-lg">
              <CheckCircle className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-emerald-700 tracking-tight">{formatMoney(totalReconciled)}</span>
            <div className="flex items-center space-x-1.5 mt-1 text-xs text-emerald-800 font-medium">
              <span>{ratePct}% do faturado</span>
              <span>•</span>
              <span>{summary?.reconciled_count || 0} pares exatos</span>
            </div>
          </div>
        </div>

        {/* Saldo em Aberto */}
        <div className="bg-white p-5 rounded-xl border border-amber-200 bg-amber-50/20 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider">Saldo em Aberto</span>
            <span className="p-2 bg-amber-100 text-amber-700 rounded-lg">
              <Clock className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-amber-700 tracking-tight">{formatMoney(totalOpen)}</span>
            <p className="text-xs text-amber-800 font-medium mt-1">
              {summary?.open_invoices_count || 0} títulos pendentes de quitação
            </p>
          </div>
        </div>
      </div>

      {/* Secondary Metrics & Monthly Evolution Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LADO ESQUERDO: COMPOSIÇÃO DO SALDO FINAL (NOTAS EM ABERTO + DIVERGÊNCIAS + SALDO ANTERIOR) */}
        <div className="lg:col-span-4 bg-white p-5 rounded-xl border-2 border-blue-200 bg-gradient-to-b from-blue-50/40 via-white to-white shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-blue-100 pb-3">
              <div className="flex items-center space-x-2">
                <span className="p-1.5 bg-blue-600 text-white rounded-lg">
                  <Scale className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-navy-950 uppercase tracking-wide">
                    Composição Saldo Final
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    O que compõe o saldo contábil exercido
                  </p>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                Auditoria Direta
              </span>
            </div>


            <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-200 text-[11px] text-blue-900 leading-relaxed">
              <strong>Conven{"\u00e7\u00e3"}o cont{"\u00e1"}bil:</strong>
              {" "}d{"\u00e9"}bitos positivos e cr{"\u00e9"}ditos negativos.
              {" "}Os valores abaixo representam os saldos residuais.
            </div>

            {!closingReadyV5 ? (
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900">
                Fechamento indispon{"\u00ed"}vel.
                Atualize o documento ou reinicie o backend.
              </div>
            ) : (
              <div className="space-y-2.5">

                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-2">
                  <div className="flex justify-between gap-2">
                    <span>Saldo anterior original</span>
                    <strong className="font-mono">
                      {closingMoneyV5(closingV5.opening_original)}
                    </strong>
                  </div>

                  <div className="flex justify-between gap-2">
                    <span>Baixas do saldo anterior</span>
                    <strong className="font-mono text-emerald-700">
                      {closingMoneyV5(closingV5.opening_paid)}
                    </strong>
                  </div>

                  <p className="text-[10px] text-slate-500">
                    Valores informativos, n{"\u00e3"}o somados novamente.
                  </p>
                </div>

                {closingRowsV5
                  .filter((row) =>
                    row.key !== "other_residual"
                    || Number(closingV5.other_residual) !== 0
                    || closingV5.unknown_count > 0
                  )
                  .map((row) => (
                    <button
                      key={row.key}
                      type="button"
                      disabled={!row.tab}
                      onClick={() => row.tab && onNavigateTab(row.tab)}
                      className={`w-full flex items-center justify-between gap-2 p-2.5 rounded-lg border text-xs text-left ${row.style} ${
                        row.tab ? "cursor-pointer hover:opacity-80" : ""
                      }`}
                    >
                      <span className="font-semibold">{row.label}</span>
                      <span className="font-mono font-bold whitespace-nowrap">
                        {closingMoneyV5(closingV5[row.key])}
                      </span>
                    </button>
                  ))}

                {Number(closingV5.opening_original) !== 0
                  && !closingV5.opening_complete && (
                  <div className="p-2 rounded-lg border border-amber-200 bg-amber-50 text-[11px] text-amber-900">
                    {closingV5.opening_attached
                      ? "Saldo anterior com documenta\u00e7\u00e3o incompleta."
                      : "Saldo anterior sem planilha complementar."}
                  </div>
                )}

                <div className="p-3 rounded-lg bg-navy-900 text-white space-y-3">
                  <div className="flex justify-between items-center gap-2">
                    <span className="text-xs font-bold text-blue-200">
                      Saldo Final Composto
                    </span>
                    <strong className={`font-mono ${
                      closingValidV5 ? "text-emerald-400" : "text-amber-300"
                    }`}>
                      {closingMoneyV5(closingV5.total)}
                    </strong>
                  </div>

                  <div className="flex justify-between gap-2 text-xs">
                    <span>Saldo informado no raz{"\u00e3"}o</span>
                    <strong className="font-mono">
                      {closingMoneyV5(closingV5.reported)}
                    </strong>
                  </div>

                  <div className="border-t border-slate-600 pt-2 flex justify-between gap-2 text-xs">
                    <span>Diferen{"\u00e7"}a cont{"\u00e1"}bil</span>
                    <strong className={`font-mono ${
                      closingValidV5 ? "text-emerald-400" : "text-amber-300"
                    }`}>
                      {closingMoneyV5(closingV5.difference)}
                    </strong>
                  </div>
                </div>

                <div className={`p-2.5 rounded-lg border text-xs font-semibold ${
                  closingValidV5
                    ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                    : "bg-rose-50 border-rose-200 text-rose-800"
                }`}>
                  {closingValidV5
                    ? "Fechamento matem\u00e1tico validado"
                    : "Fechamento exige revis\u00e3o"}
                </div>

              </div>
            )}
          </div>

          {/* Botões de Ação Rápida */}
          <div className="mt-4 pt-3 border-t border-slate-200 grid grid-cols-2 gap-2">
            <button
              onClick={() => onNavigateTab("open")}
              className="py-1.5 px-2 text-center text-xs font-semibold bg-amber-100 hover:bg-amber-200 text-amber-900 rounded-lg transition"
            >
              Ver em Aberto
            </button>
            <button
              onClick={() => onNavigateTab("divergences")}
              className="py-1.5 px-2 text-center text-xs font-semibold bg-rose-100 hover:bg-rose-200 text-rose-900 rounded-lg transition"
            >
              Ver Divergências
            </button>
          </div>
        </div>

        {/* LADO DIREITO: Evolução Mensal & Resumo de Auditoria */}
        <div className="lg:col-span-8 space-y-6">
          {/* Monthly Breakdown Card */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900 tracking-tight">Evolução Mensal: Débitos vs Créditos</h3>
                <p className="text-xs text-slate-500">Movimentação contábil discriminada por competência</p>
              </div>
              <span className="text-xs font-mono font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md">
                {validMonthCountV5} {validMonthCountV5 === 1 ? "m\u00eas" : "meses"}
              </span>
            </div>

            <div className="space-y-4">
              {monthlyEvolution?.map((m) => {
                const maxVal = Math.max(
                  ...monthlyEvolution.map((x) => Math.max(x.credits, x.debits)),
                  1
                );
                const credPct = Math.round((m.credits / maxVal) * 100);
                const debPct = Math.round((m.debits / maxVal) * 100);

                return (
                  <div key={m.month} className="space-y-1 text-xs">
                    <div className="flex justify-between font-mono font-medium text-slate-700">
                      <span className="font-bold text-slate-900">{formatMonthV5(m.month)}</span>
                      <span>Crédito: {formatMoney(m.credits)} | Débito: {formatMoney(m.debits)}</span>
                    </div>
                    {/* Credit bar */}
                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden flex">
                      <div 
                        className="bg-blue-600 h-full rounded-full transition-all duration-500" 
                        style={{ width: `${credPct}%` }}
                        title={`Crédito: ${formatMoney(m.credits)}`}
                      />
                    </div>
                    {/* Debit bar */}
                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden flex">
                      <div 
                        className="bg-emerald-500 h-full rounded-full transition-all duration-500" 
                        style={{ width: `${debPct}%` }}
                        title={`Débito: ${formatMoney(m.debits)}`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-end space-x-4 mt-4 pt-3 border-t border-slate-100 text-xs">
              <div className="flex items-center space-x-1.5">
                <span className="w-3 h-3 rounded-sm bg-blue-600"></span>
                <span className="text-slate-600">Entradas (Créditos)</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="w-3 h-3 rounded-sm bg-emerald-500"></span>
                <span className="text-slate-600">Pagamentos (Débitos)</span>
              </div>
            </div>
          </div>

          {/* Auditoria & Memória de Cálculo Resumida */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="space-y-1 text-xs">
              <span className="font-bold text-slate-800">Equação Geral de Fechamento Contábil:</span>

              <p className="text-slate-500">
                Saldo inicial ({formatMoney(initialBalance)})
                {" + "}d{"\u00e9"}bitos ({formatMoney(totalDebits)})
                {" - "}cr{"\u00e9"}ditos ({formatMoney(totalCredits)})
                {" = "}saldo final informado ({formatMoney(finalReported)}).
              </p>
              <p className="text-slate-500">
                Movimento l{"\u00ed"}quido: {formatMoney(periodNet)}.
                {" "}A composi{"\u00e7\u00e3"}o residual {"\u00e9"} conferida
                separadamente com o saldo do raz{"\u00e3"}o.
              </p>
            </div>
            <button
              onClick={onOpenAudit}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold rounded-lg text-xs transition border border-slate-300 whitespace-nowrap"
            >
              Exibir Memória Completa
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
