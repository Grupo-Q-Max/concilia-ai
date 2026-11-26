"use client";

import React, { useState, useMemo, useRef } from "react";
import { 
  GitMerge, 
  Search, 
  Check, 
  AlertCircle, 
  ArrowRight, 
  Filter, 
  Equal, 
  Building2,
  DollarSign,
  FileText,
  ChevronDown,
  ChevronUp,
  Loader2
} from "lucide-react";
import { Transaction } from "@/lib/api";
import { displayNf } from "@/components/SmartSuggestions";

interface ManualMatchModalProps {
  openInvoices: Transaction[];
  unmappedPayments: Transaction[];
  // CONCILIA_V5_MANUAL_UI_30A3C4A
  onConfirmMatch: (
    invId: string,
    payId: string,
    expectedInvoiceRemaining: string,
    expectedPaymentRemaining: string
  ) => Promise<void>;
}

export const ManualMatchModal: React.FC<ManualMatchModalProps> = ({
  openInvoices,
  unmappedPayments,
  onConfirmMatch
}) => {
  const [selectedInv, setSelectedInv] = useState<string | null>(null);
  const [selectedPay, setSelectedPay] = useState<string | null>(null);
  
  // Filtros
  const [filterSameAmount, setFilterSameAmount] = useState(false);
  const [searchInv, setSearchInv] = useState("");
  const [searchPay, setSearchPay] = useState("");

  // Visualização de Histórico Completo
  const [showFullHistory, setShowFullHistory] = useState(false);
  const [expandedHistories, setExpandedHistories] = useState<Set<string>>(new Set());

  const [loading, setLoading] = useState(false);
  const manualBusyV5 = useRef(false);

  const toggleItemHistory = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setExpandedHistories(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const strictResidualV5 = (value: unknown): string => {
    if (typeof value !== "string" && typeof value !== "number") {
      throw new Error("Saldo residual ausente. Atualize os dados.");
    }

    const raw = String(value).trim();

    if (!/^\d+(?:\.\d{1,2})?$/.test(raw)) {
      throw new Error("Saldo residual invalido. Atualize os dados.");
    }

    const parts = raw.split(".");
    const whole = parts[0].replace(/^0+(?=\d)/, "");
    const fraction = (parts[1] || "").padEnd(2, "0");
    const normalized = whole + "." + fraction;

    if (!/[1-9]/.test(normalized)) {
      throw new Error("O saldo residual deve ser positivo.");
    }

    return normalized;
  };

  const [msg, setMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const formatMoney = (val: any) => {
    const num = parseFloat(val || 0);
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  // Conjuntos de valores para o filtro de mesmo valor
  const invoiceAmounts = useMemo(() => {
    return new Set(openInvoices.map((i) => parseFloat(String(i.remaining_amount || i.amount || "0")).toFixed(2)));
  }, [openInvoices]);

  const paymentAmounts = useMemo(() => {
    return new Set(unmappedPayments.map((p) => parseFloat(String(p.remaining_amount || p.amount || "0")).toFixed(2)));
  }, [unmappedPayments]);

  // Valores comuns existentes em ambos os lados
  const commonAmounts = useMemo(() => {
    const common = new Set<string>();
    invoiceAmounts.forEach((amt) => {
      if (paymentAmounts.has(amt)) {
        common.add(amt);
      }
    });
    return common;
  }, [invoiceAmounts, paymentAmounts]);

  // Lista filtrada de Notas em Aberto
  const filteredInvoices = useMemo(() => {
    return openInvoices.filter((inv) => {
      const amtStr = parseFloat(String(inv.remaining_amount || inv.amount || "0")).toFixed(2);
      if (filterSameAmount && !commonAmounts.has(amtStr)) {
        return false;
      }
      if (searchInv) {
        const q = searchInv.toLowerCase();
        const nfVal = displayNf(inv.extracted_nf, inv.history);
        const matchesNf = (inv.extracted_nf && inv.extracted_nf.toLowerCase().includes(q)) || (nfVal && nfVal.toLowerCase().includes(q));
        const matchesSup = inv.extracted_supplier && inv.extracted_supplier.toLowerCase().includes(q);
        const matchesHist = inv.history && inv.history.toLowerCase().includes(q);
        const matchesVal = amtStr.includes(q);
        return matchesNf || matchesSup || matchesHist || matchesVal;
      }
      return true;
    });
  }, [openInvoices, filterSameAmount, commonAmounts, searchInv]);

  // Lista filtrada de Pagamentos Pendentes
  const filteredPayments = useMemo(() => {
    return unmappedPayments.filter((pay) => {
      const amtStr = parseFloat(String(pay.remaining_amount || pay.amount || "0")).toFixed(2);
      if (filterSameAmount && !commonAmounts.has(amtStr)) {
        return false;
      }
      if (searchPay) {
        const q = searchPay.toLowerCase();
        const matchesSup = pay.extracted_supplier && pay.extracted_supplier.toLowerCase().includes(q);
        const matchesHist = pay.history && pay.history.toLowerCase().includes(q);
        const matchesVal = amtStr.includes(q);
        return matchesSup || matchesHist || matchesVal;
      }
      return true;
    });
  }, [unmappedPayments, filterSameAmount, commonAmounts, searchPay]);

  const invObj = openInvoices.find((i) => i.id === selectedInv);
  const payObj = unmappedPayments.find((p) => p.id === selectedPay);

  // Auto-sugestão ao clicar numa nota ou pagamento se tiver valor idêntico
  const handleSelectInvoice = (invId: string) => {
    setSelectedInv(invId);
    const chosen = openInvoices.find((i) => i.id === invId);
    if (chosen) {
      const amt = parseFloat(String(chosen.remaining_amount || chosen.amount || "0")).toFixed(2);
      const matchingPay = unmappedPayments.find(
        (p) => parseFloat(String(p.remaining_amount || p.amount || "0")).toFixed(2) === amt
      );
      if (matchingPay) {
        setSelectedPay(matchingPay.id);
      }
    }
  };

  const handleSelectPayment = (payId: string) => {
    setSelectedPay(payId);
    const chosen = unmappedPayments.find((p) => p.id === payId);
    if (chosen) {
      const amt = parseFloat(String(chosen.remaining_amount || chosen.amount || "0")).toFixed(2);
      const matchingInv = openInvoices.find(
        (i) => parseFloat(String(i.remaining_amount || i.amount || "0")).toFixed(2) === amt
      );
      if (matchingInv) {
        setSelectedInv(matchingInv.id);
      }
    }
  };

  const handleMatch = async () => {
    if (!selectedInv || !selectedPay || manualBusyV5.current) return;

    manualBusyV5.current = true;
    setLoading(true);
    setMsg(null);

    try {
      const invoice = openInvoices.find(
        item => item.id === selectedInv
      );

      const payment = unmappedPayments.find(
        item => item.id === selectedPay
      );

      if (!invoice || !payment) {
        throw new Error(
          "Lancamentos nao encontrados. Atualize os dados."
        );
      }

      const expectedInvoiceRemaining = strictResidualV5(
        invoice.remaining_amount
      );

      const expectedPaymentRemaining = strictResidualV5(
        payment.remaining_amount
      );

      const approved = window.confirm(
        "Confirmar conciliacao manual?\n\n" +
        "Saldo da nota: " +
        formatMoney(expectedInvoiceRemaining) +
        "\nSaldo do pagamento: " +
        formatMoney(expectedPaymentRemaining) +
        "\n\nA baixa sera limitada ao menor saldo.\n" +
        "Confirme somente apos revisar os lancamentos."
      );

      if (!approved) return;

      await onConfirmMatch(
        selectedInv,
        selectedPay,
        expectedInvoiceRemaining,
        expectedPaymentRemaining
      );
      setMsg({ text: "Conciliação manual aplicada e auditada com sucesso!", type: "success" });
      setSelectedInv(null);
      setSelectedPay(null);
    } catch (err: any) {
      setMsg({ text: `Erro ao conciliar: ${err.message}`, type: "error" });
    } finally {
      manualBusyV5.current = false;
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
      {/* Cabeçalho */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <span className="p-1.5 bg-blue-100 text-blue-700 rounded-lg">
              <GitMerge className="w-5 h-5" />
            </span>
            <span>Conciliação Manual Assistida</span>
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Selecione uma nota de provisão em aberto e um pagamento pendente para efetuar a baixa manual controlada.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Botão de Exibição de Histórico Completo */}
          <button
            type="button"
            onClick={() => setShowFullHistory(!showFullHistory)}
            className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center space-x-1.5 border transition ${
              showFullHistory
                ? "bg-slate-800 text-white border-slate-800 shadow-sm"
                : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-300"
            }`}
            title="Alternar visualização completa de todos os históricos sem cortes"
          >
            <FileText className="w-4 h-4" />
            <span>{showFullHistory ? "Histórico Resumido" : "Ler Histórico Completo"}</span>
          </button>

          {/* Botão de Filtro Rápido: Notas e Pagamentos com Mesmo Valor */}
          <button
            type="button"
            onClick={() => setFilterSameAmount(!filterSameAmount)}
            className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 border transition ${
              filterSameAmount
                ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-300"
            }`}
          >
            <Equal className="w-4 h-4" />
            <span>Filtrar Mesmo Valor</span>
            {commonAmounts.size > 0 && (
              <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${filterSameAmount ? "bg-white text-blue-700" : "bg-blue-100 text-blue-800"}`}>
                {commonAmounts.size} compatíveis
              </span>
            )}
          </button>
        </div>
      </div>

      {msg ? (
        <div
          className={`p-3 rounded-lg text-xs font-medium border flex items-center space-x-2 ${
            msg.type === "success"
              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
              : "bg-rose-50 text-rose-800 border-rose-200"
          }`}
        >
          {msg.type === "success" ? <Check className="w-4 h-4 text-emerald-600" /> : <AlertCircle className="w-4 h-4 text-rose-600" />}
          <span>{msg.text}</span>
        </div>
      ) : null}

      {/* Grid de Seleção */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Coluna 1: Notas Fiscais em Aberto */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center space-x-1.5">
              <span>1. Notas Fiscais em Aberto</span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                {filteredInvoices.length} de {openInvoices.length}
              </span>
            </h4>
          </div>

          {/* Campo de Busca de Notas */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar por NF, fornecedor ou valor..."
              value={searchInv}
              onChange={(e) => setSearchInv(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-slate-50/50"
            />
          </div>

          <div className="max-h-96 overflow-y-auto space-y-2 pr-1 border border-slate-200 rounded-lg p-2 bg-slate-50">
            {filteredInvoices.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                {filterSameAmount ? "Nenhuma nota com mesmo valor de pagamentos pendentes." : "Nenhuma nota em aberto encontrada."}
              </div>
            ) : (
              filteredInvoices.map((inv) => {
                const amt = parseFloat(String(inv.remaining_amount || inv.amount || "0")).toFixed(2);
                const hasMatchingPay = paymentAmounts.has(amt);
                const isSelected = selectedInv === inv.id;
                const isHistExpanded = showFullHistory || expandedHistories.has(inv.id);

                return (
                  <div
                    key={inv.id}
                    onClick={() => handleSelectInvoice(inv.id)}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition relative ${
                      isSelected
                        ? "bg-amber-100/90 border-amber-500 shadow-sm ring-1 ring-amber-500"
                        : "bg-white border-slate-200 hover:border-amber-300"
                    }`}
                  >
                    <div className="flex justify-between font-bold text-slate-900">
                      <div className="flex items-center space-x-1.5">
                        <span className="text-blue-700 font-bold">NF {displayNf(inv.extracted_nf, inv.history)}</span>
                        {hasMatchingPay && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            Valor Compatível
                          </span>
                        )}
                      </div>
                      <span className="font-mono font-bold text-amber-800">{formatMoney(inv.remaining_amount)}</span>
                    </div>

                    <p className="text-[11px] text-slate-700 font-semibold truncate mt-1" title={inv.extracted_supplier}>
                      {inv.extracted_supplier || "Sem fornecedor claro"}
                    </p>

                    {/* Exibição do Histórico */}
                    {isHistExpanded ? (
                      <div className="mt-1.5 p-2 rounded bg-amber-50 border border-amber-200 text-[11px] font-mono text-slate-800 break-words whitespace-pre-wrap select-text leading-relaxed">
                        <div className="flex justify-between items-center text-[10px] text-amber-900 font-semibold mb-1">
                          <span>Data: {inv.trans_date} • Histórico Completo:</span>
                          <button
                            type="button"
                            onClick={(e) => toggleItemHistory(inv.id, e)}
                            className="text-amber-700 hover:text-amber-950 font-bold underline"
                          >
                            recolher
                          </button>
                        </div>
                        {inv.history || "Sem histórico"}
                      </div>
                    ) : (
                      <div className="mt-0.5 flex items-start justify-between gap-1.5">
                        <p className="text-[10px] text-slate-500 font-mono line-clamp-1 flex-1" title={inv.history}>
                          {inv.trans_date} • {inv.history}
                        </p>
                        <button
                          type="button"
                          onClick={(e) => toggleItemHistory(inv.id, e)}
                          className="text-[10px] text-blue-600 hover:text-blue-800 font-semibold shrink-0 hover:underline"
                        >
                          Ler mais
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Coluna 2: Pagamentos Pendentes */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 flex items-center space-x-1.5">
              <span>2. Pagamentos Pendentes</span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                {filteredPayments.length} de {unmappedPayments.length}
              </span>
            </h4>
          </div>

          {/* Campo de Busca de Pagamentos */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar por fornecedor, histórico ou valor..."
              value={searchPay}
              onChange={(e) => setSearchPay(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50"
            />
          </div>

          <div className="max-h-96 overflow-y-auto space-y-2 pr-1 border border-slate-200 rounded-lg p-2 bg-slate-50">
            {filteredPayments.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                {filterSameAmount ? "Nenhum pagamento com valor idêntico às notas em aberto." : "Nenhum pagamento sem provisão pendente."}
              </div>
            ) : (
              filteredPayments.map((pay) => {
                const amt = parseFloat(String(pay.remaining_amount || pay.amount || "0")).toFixed(2);
                const hasMatchingInv = invoiceAmounts.has(amt);
                const isSelected = selectedPay === pay.id;
                const isHistExpanded = showFullHistory || expandedHistories.has(pay.id);

                return (
                  <div
                    key={pay.id}
                    onClick={() => handleSelectPayment(pay.id)}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition relative ${
                      isSelected
                        ? "bg-blue-100/90 border-blue-500 shadow-sm ring-1 ring-blue-500"
                        : "bg-white border-slate-200 hover:border-blue-300"
                    }`}
                  >
                    <div className="flex justify-between font-bold text-slate-900">
                      <div className="flex items-center space-x-1.5">
                        <span className="text-slate-800 font-bold">Lançamento #{pay.row_index}</span>
                        {hasMatchingInv && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            Valor Compatível
                          </span>
                        )}
                      </div>
                      <span className="font-mono font-bold text-blue-800">{formatMoney(pay.remaining_amount)}</span>
                    </div>

                    <p className="text-[11px] text-slate-700 font-semibold truncate mt-1" title={pay.extracted_supplier}>
                      {pay.extracted_supplier || "Sem fornecedor claro"}
                    </p>

                    {/* Exibição do Histórico */}
                    {isHistExpanded ? (
                      <div className="mt-1.5 p-2 rounded bg-blue-50 border border-blue-200 text-[11px] font-mono text-slate-800 break-words whitespace-pre-wrap select-text leading-relaxed">
                        <div className="flex justify-between items-center text-[10px] text-blue-900 font-semibold mb-1">
                          <span>Data: {pay.trans_date} • Histórico Completo:</span>
                          <button
                            type="button"
                            onClick={(e) => toggleItemHistory(pay.id, e)}
                            className="text-blue-700 hover:text-blue-950 font-bold underline"
                          >
                            recolher
                          </button>
                        </div>
                        {pay.history || "Sem histórico"}
                      </div>
                    ) : (
                      <div className="mt-0.5 flex items-start justify-between gap-1.5">
                        <p className="text-[10px] text-slate-500 font-mono line-clamp-1 flex-1" title={pay.history}>
                          {pay.trans_date} • {pay.history}
                        </p>
                        <button
                          type="button"
                          onClick={(e) => toggleItemHistory(pay.id, e)}
                          className="text-[10px] text-blue-600 hover:text-blue-800 font-semibold shrink-0 hover:underline"
                        >
                          Ler mais
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* PAINEL DE AUDITORIA E COMPARAÇÃO DOS SELECIONADOS */}
      {(invObj || payObj) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
          {/* Detalhes Nota Selecionada */}
          {invObj ? (
            <div className="p-3.5 bg-amber-50/90 rounded-lg border border-amber-300 text-xs space-y-2">
              <div className="flex justify-between items-center font-bold text-amber-950 border-b border-amber-200 pb-1.5">
                <span className="text-sm">Nota Fiscal: NF {displayNf(invObj.extracted_nf, invObj.history)}</span>
                <span className="font-mono text-sm text-amber-900">{formatMoney(invObj.remaining_amount)}</span>
              </div>
              <p className="font-semibold text-slate-800">{invObj.extracted_supplier || "Fornecedor não identificado"}</p>
              <p className="text-[11px] text-slate-600">Data de Emissão: <strong className="font-mono">{invObj.trans_date}</strong></p>
              <div className="mt-1">
                <span className="text-[10px] font-bold text-amber-900 uppercase tracking-wider">Histórico Integral da Provisão:</span>
                <div className="mt-1 p-2 bg-white rounded border border-amber-200 font-mono text-[11px] text-slate-900 break-words whitespace-pre-wrap select-text leading-relaxed">
                  {invObj.history}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-lg border-2 border-dashed border-amber-200 text-center text-amber-700 text-xs italic flex items-center justify-center">
              Selecione uma nota fiscal na coluna 1 para revisar os detalhes.
            </div>
          )}

          {/* Detalhes Pagamento Selecionado */}
          {payObj ? (
            <div className="p-3.5 bg-blue-50/90 rounded-lg border border-blue-300 text-xs space-y-2">
              <div className="flex justify-between items-center font-bold text-blue-950 border-b border-blue-200 pb-1.5">
                <span className="text-sm">Pagamento: Lançamento #{payObj.row_index}</span>
                <span className="font-mono text-sm text-blue-900">{formatMoney(payObj.remaining_amount)}</span>
              </div>
              <p className="font-semibold text-slate-800">{payObj.extracted_supplier || "Sem fornecedor identificado"}</p>
              <p className="text-[11px] text-slate-600">Data do Pagamento: <strong className="font-mono">{payObj.trans_date}</strong></p>
              <div className="mt-1">
                <span className="text-[10px] font-bold text-blue-900 uppercase tracking-wider">Histórico Integral do Pagamento:</span>
                <div className="mt-1 p-2 bg-white rounded border border-blue-200 font-mono text-[11px] text-slate-900 break-words whitespace-pre-wrap select-text leading-relaxed">
                  {payObj.history}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-lg border-2 border-dashed border-blue-200 text-center text-blue-700 text-xs italic flex items-center justify-center">
              Selecione um pagamento na coluna 2 para revisar os detalhes.
            </div>
          )}
        </div>
      )}

      {/* Barra de Ação e Associação */}
      <div className="p-4 bg-slate-100/90 rounded-xl border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-xs text-slate-700">
          {invObj && payObj ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-amber-900 bg-amber-100 px-2.5 py-1 rounded border border-amber-200">
                NF {displayNf(invObj.extracted_nf, invObj.history)}: {formatMoney(invObj.remaining_amount)}
              </span>
              <ArrowRight className="w-4 h-4 text-slate-400" />
              <span className="font-bold text-blue-900 bg-blue-100 px-2.5 py-1 rounded border border-blue-200">
                Pagamento: {formatMoney(payObj.remaining_amount)}
              </span>
              {parseFloat(invObj.remaining_amount) === parseFloat(payObj.remaining_amount) ? (
                <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                  ✓ Valores 100% Iguais
                </span>
              ) : (
                <span className="text-[11px] font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded">
                  Diferença: {formatMoney(Math.abs(parseFloat(invObj.remaining_amount) - parseFloat(payObj.remaining_amount)))}
                </span>
              )}
            </div>
          ) : (
            <span className="text-slate-500 italic">
              Selecione uma nota fiscal à esquerda e um pagamento à direita para associar.
            </span>
          )}
        </div>

        <button
          disabled={!selectedInv || !selectedPay || loading}
          onClick={handleMatch}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold shadow-md transition disabled:cursor-not-allowed whitespace-nowrap flex items-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Conciliando e auditando...</span>
            </>
          ) : (
            <span>Confirmar Conciliação Manual</span>
          )}
        </button>
      </div>
    </div>
  );
};
