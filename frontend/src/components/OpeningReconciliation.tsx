
"use client";

// CONCILIA_V5_EXPORT_BUTTON_24D
import ExportSuggestionsButton from "@/components/ExportSuggestionsButton";
import { OpeningUploadModal } from "@/components/OpeningUploadModal";


import React, {
  useState,
  useEffect,
  useRef,
  useCallback
} from "react";

import {
  getOpeningSuggestionsV5,
  approveOpeningV5,
  attachOpening,
  api,
  OpeningDataV5,
  OpeningSuggestionV5,
  Transaction
} from "@/lib/api";
import { displayNf } from "@/components/SmartSuggestions";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCheck,
  Loader2,
  AlertCircle,
  CheckCircle2,
  X
} from "lucide-react";

type Props = {
  revision: number;
  jobId: string;
  initialBalance: string;
  composition: any;
  onRefresh: () => Promise<void>;
};

const fmt = (v: any) =>
  Number(v || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });

const nature = (v: any) =>
  fmt(Math.abs(Number(v || 0))) +
  (Number(v) < 0 ? " C" : Number(v) > 0 ? " D" : "");

const errorText = (e: unknown) =>
  e instanceof Error ? e.message : String(e);

export default function OpeningReconciliation({
  revision,
  jobId,
  initialBalance,
  composition,
  onRefresh
}: Props) {

  const [data, setData] = useState<OpeningDataV5 | null>(null);
  const [payments, setPayments] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(30);

  const [batchProgress, setBatchProgress] = useState<{
    total: number;
    current: number;
    currentNf: string;
    currentAmount: string;
  } | null>(null);

  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedUploadFile, setSelectedUploadFile] = useState<File | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  const lock = useRef(false);
  const request = useRef(0);

  const load = useCallback(async () => {

    const seq = ++request.current;

    setLoading(true);

    try {

      const [result, tx] = await Promise.all([
        getOpeningSuggestionsV5(jobId),
        api.getTransactions(jobId, {trans_type: "DEBIT"})
      ]);

      if (
        !Array.isArray(result.items) ||
        !Array.isArray(result.opening_rows) ||
        !Array.isArray(tx)
      ) {
        throw new Error("Dados do saldo anterior invalidos.");
      }

      if (seq === request.current) {
        setData(result);
        setPayments(tx);
      }

    } catch (e) {

      if (seq === request.current) {
        setData(null);
        setError(errorText(e));
      }

    } finally {

      if (seq === request.current) {
        setLoading(false);
      }

    }

  }, [jobId]);

  useEffect(() => {

    // Preserve the result of the last operation.
    void load();

    return () => {
      request.current++;
    };

  }, [load, composition?.opening_attached, revision]);

  const approve = async (item: OpeningSuggestionV5) => {

    if (lock.current || loading) return;

    const warning = item.ambiguous || item.current_conflict
      ? "\nATENCAO: existem outros vinculos possiveis."
      : "";

    if (!window.confirm(
      "Confirma a baixa do saldo anterior?\n" +
      "Valor da baixa: " +
      fmt(Math.min(
        Number(item.opening_amount),
        Number(item.payment_amount)
      )) +
      warning
    )) return;

    lock.current = true;

    setBusy(true);
    setError("");
    setMessage("");

    try {

      const result = await approveOpeningV5(jobId, item);

      if (!result.success) {
        throw new Error("Baixa nao confirmada pelo servidor.");
      }

      setMessage(
        "Baixa registrada: " +
        fmt(result.reconciled_amount) +
        ". Saldo contabil preservado."
      );

      try {

        await onRefresh();

      } catch (e) {

        setError(
          "Baixa registrada, mas a composicao precisa ser atualizada: " +
          errorText(e)
        );

      }

    } catch (e) {

      setError(errorText(e));

    } finally {

      await load();

      lock.current = false;
      setBusy(false);

    }

  };

  const handleFileUpload = (file: File) => {
    if (!file) return;
    setUploadError("");
    setError("");
    setMessage("");
    setSelectedUploadFile(file);
    setIsUploadModalOpen(true);
  };

  const getItemKey = (item: OpeningSuggestionV5) =>
    `${item.opening_index}:${item.payment_trans_id}`;

  const eligibleItems = (data?.items || []).filter(
    item => item.automatic_eligible && !item.ambiguous && !item.current_conflict
  );

  const selectedItems = (data?.items || []).filter(item =>
    selectedKeys.has(getItemKey(item))
  );

  const totalSelectedAmount = selectedItems.reduce((acc, item) => {
    return acc + Math.min(Number(item.opening_amount || 0), Number(item.payment_amount || 0));
  }, 0);

  const handleBatchApprove = async (
    itemsToApprove: OpeningSuggestionV5[],
    mode: "COMPATIBLE" | "SELECTED" = "COMPATIBLE"
  ) => {
    if (lock.current || busy || loading || itemsToApprove.length === 0) return;

    const count = itemsToApprove.length;
    const reviewCount = itemsToApprove.filter(
      s => s.ambiguous || s.current_conflict || s.category !== "EXATO"
    ).length;

    const confirmMsg =
      mode === "SELECTED"
        ? reviewCount > 0
          ? `Confirmar aprovação simultânea de ${count} baixa(s) selecionada(s)? (${reviewCount} possuem observações/divergências e serão confirmadas).`
          : `Confirmar aprovação simultânea de ${count} baixa(s) do saldo anterior selecionada(s)?`
        : `Deseja aprovar automaticamente ${count} baixas compatíveis do saldo anterior?\nO saldo contábil e as composições serão preservados.`;

    if (!window.confirm(confirmMsg)) return;

    lock.current = true;
    setBusy(true);
    setError("");
    setMessage("");

    let completed = 0;
    const failed: string[] = [];

    try {
      for (let i = 0; i < itemsToApprove.length; i++) {
        const item = itemsToApprove[i];
        const nf = displayNf(item.opening_nf, rows[item.opening_index]?.history);
        const amount = fmt(Math.min(Number(item.opening_amount), Number(item.payment_amount)));

        setBatchProgress({
          total: itemsToApprove.length,
          current: i + 1,
          currentNf: nf,
          currentAmount: amount
        });

        try {
          const res = await approveOpeningV5(jobId, item);
          if (res.success) {
            completed++;
            setSelectedKeys(prev => {
              const next = new Set(prev);
              next.delete(getItemKey(item));
              return next;
            });
          } else {
            failed.push(`NF ${nf}: ${res.detail || "Falha ao registrar baixa."}`);
          }
        } catch (e: unknown) {
          failed.push(`NF ${nf}: ${errorText(e)}`);
        }
      }

      setMessage(
        `Sucesso: ${completed} baixas do saldo anterior aprovadas e registradas com sucesso!` +
        (failed.length > 0 ? ` (${failed.length} pendentes de conferência manual).` : "")
      );

      try {
        await onRefresh();
      } catch (e) {
        // ignore refresh error
      }
    } finally {
      setBatchProgress(null);
      await load();
      lock.current = false;
      setBusy(false);
    }
  };

  const rows = data?.opening_rows || [];

  const creditorResidual = rows.reduce(
    (sum, r) => sum + Math.max(0, -Number(r.value || 0)),
    0
  );

  const debtorResidual = rows.reduce(
    (sum, r) => sum + Math.max(0, Number(r.value || 0)),
    0
  );

  const paymentMap = new Map(
    payments.map(p => [p.id, p])
  );

  const filtered = (data?.items || []).filter(item => {

    const inv = rows[item.opening_index];
    const pay = paymentMap.get(item.payment_trans_id);

    if (filter === "AMBIGUOUS" && !item.ambiguous) return false;

    if (
      filter !== "ALL" &&
      filter !== "AMBIGUOUS" &&
      item.category !== filter
    ) return false;

    const text = [
      inv?.extracted_nf,
      displayNf(item.opening_nf || inv?.extracted_nf, inv?.history),
      inv?.extracted_supplier,
      inv?.history,
      pay?.extracted_nf,
      displayNf(item.payment_nf || pay?.extracted_nf, pay?.history),
      pay?.extracted_supplier,
      pay?.history,
      item.reason
    ].join(" ").toLowerCase();

    return text.includes(search.toLowerCase());

  });

  const visibleItems = filtered.slice(0, limit);
  const allVisibleSelected =
    visibleItems.length > 0 &&
    visibleItems.every(item => selectedKeys.has(getItemKey(item)));

  const toggleSelectAllVisible = () => {
    if (allVisibleSelected) {
      setSelectedKeys(prev => {
        const next = new Set(prev);
        for (const item of visibleItems) {
          next.delete(getItemKey(item));
        }
        return next;
      });
    } else {
      setSelectedKeys(prev => {
        const next = new Set(prev);
        for (const item of visibleItems) {
          next.add(getItemKey(item));
        }
        return next;
      });
    }
  };

  const toggleSelectItem = (item: OpeningSuggestionV5) => {
    const key = getItemKey(item);
    setSelectedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  return (
    <section className="border border-slate-200 rounded-xl p-5 space-y-4">

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">

        <div>
          <p className="text-sm font-bold text-slate-800">
            Relatorio do saldo anterior
          </p>

          <p className="text-xs text-slate-500">
            Composicao, sugestoes, residuais e baixas realizadas.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {data?.opening_attached && (
            <button
              type="button"
              disabled={busy || loading}
              onClick={() => {
                setSelectedUploadFile(null);
                setIsUploadModalOpen(true);
              }}
              className="inline-flex items-center gap-1.5 border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer transition-colors shadow-2xs"
            >
              <UploadCloud className="w-3.5 h-3.5 text-blue-600" />
              <span>Trocar / Reenviar Planilha</span>
            </button>
          )}

          <ExportSuggestionsButton
            key={jobId}
            jobId={jobId}
            tab="opening-suggestions"
            label="Exportar saldo anterior em Excel"
            disabled={busy || loading}
          />
        </div>

      </div>


      <div className="flex flex-wrap justify-between items-center gap-3">

        <div>
          <h3 className="text-lg font-bold">
            Conciliacao entre exercicios
          </h3>
          <p className="text-xs text-slate-500">
            Notas anteriores e pagamentos do exercicio atual.
          </p>
        </div>

        <button
          disabled={busy || loading}
          onClick={() => {
            setError("");
            void load();
          }}
          className="border rounded-lg px-3 py-2 text-xs"
        >
          Atualizar sugestoes
        </button>

      </div>

      {error && (
        <div role="alert" className="border border-red-300 text-red-600 rounded-lg p-3 text-sm">
          {error}
        </div>
      )}

      {message && (
        <div role="status" className="border border-emerald-300 text-emerald-600 rounded-lg p-3 text-sm">
          {message}
        </div>
      )}

      {loading && <p>Carregando saldo anterior...</p>}

      {!loading && data && !data.opening_attached && (
        <div className="border-2 border-dashed border-blue-200 bg-blue-50/40 rounded-2xl p-8 text-center space-y-3">
          <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 mx-auto flex items-center justify-center">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div>
            <h4 className="font-bold text-slate-800 text-base">
              Anexar Planilha de Saldo Anterior do Fornecedor
            </h4>
            <p className="text-xs text-slate-500 max-w-lg mx-auto mt-1">
              Envie a planilha de títulos anteriores (.xls, .xlsx, .csv). O sistema fará o cruzamento inteligente com os pagamentos do razão atual e listará as baixas para aprovação.
            </p>
          </div>
          <div className="pt-2">
            <button
              type="button"
              disabled={busy || loading}
              onClick={() => {
                setSelectedUploadFile(null);
                setIsUploadModalOpen(true);
              }}
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-5 py-2.5 rounded-xl cursor-pointer shadow-sm transition-colors"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Selecionar Planilha de Saldo Anterior</span>
            </button>
          </div>
          {uploadBusy && (
            <div className="flex items-center justify-center gap-2 text-xs font-semibold text-blue-700 pt-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Lendo, sanitizando e cruzando lançamentos anteriores...</span>
            </div>
          )}
          {uploadError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl max-w-md mx-auto text-left">
              <strong>⚠️ Erro:</strong> {uploadError}
            </div>
          )}
        </div>
      )}

      {data?.opening_attached && (

        <>

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">

            {[
              ["Saldo anterior original", nature(initialBalance)],
              ["Nao comprovado", nature(composition?.opening_difference)],
              ["Total baixado", fmt(data.approved_amount)],
              ["Creditos residuais anteriores", fmt(creditorResidual)],
              ["Debitos residuais anteriores", fmt(debtorResidual)],
              ["Baixas registradas", String(data.approved_count)]
            ].map(([label, value]) => (
              <div key={label} className="border rounded-lg p-3">
                <p className="text-xs text-slate-500">{label}</p>
                <p className="font-bold text-lg">{value}</p>
              </div>
            ))}

          </div>

          <details className="border rounded-lg p-3">

            <summary className="cursor-pointer font-semibold">
              Notas anteriores ({rows.length})
            </summary>

            <div className="overflow-auto mt-3">

              <table className="w-full text-xs">

                <thead>
                  <tr className="text-left">
                    {["NF", "Fornecedor / Historico", "Original", "Baixado", "Residual", "Status"].map(h => (
                      <th key={h} className="p-2">{h}</th>
                    ))}
                  </tr>
                </thead>

                <tbody>

                  {rows.map((r, i) => (
                    <tr key={i} className="border-t">
                      <td className="p-2">{displayNf(r.extracted_nf, r.history)}</td>
                      <td className="p-2">{r.extracted_supplier || r.history}</td>
                      <td className="p-2">{fmt(r.original)}</td>
                      <td className="p-2">{fmt(r.matched_amount)}</td>
                      <td className="p-2">{nature(r.value)}</td>
                      <td className="p-2">{r.status}</td>
                    </tr>
                  ))}

                </tbody>

              </table>

            </div>

          </details>

          <div className="flex flex-wrap gap-3 items-center justify-between">

            <div className="flex flex-wrap gap-3 items-center">
              <h4 className="font-bold">
                Sugestoes ({data.total})
              </h4>

              <input
                value={search}
                placeholder="Buscar NF ou fornecedor"
                onChange={e => {
                  setSearch(e.target.value);
                  setLimit(30);
                }}
                className="border rounded-lg px-3 py-2 text-sm"
              />

              <select
                value={filter}
                onChange={e => {
                  setFilter(e.target.value);
                  setLimit(30);
                }}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                <option value="ALL">Todas</option>
                <option value="EXATO">Exatas</option>
                <option value="PARCIAL">Parciais</option>
                <option value="DIVERGENCIA_NF">NFs diferentes</option>
                <option value="AMBIGUOUS">Ambiguas</option>
              </select>
            </div>

            {eligibleItems.length > 0 && (
              <button
                type="button"
                disabled={busy || loading}
                onClick={() => void handleBatchApprove(eligibleItems, "COMPATIBLE")}
                className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-xs transition-colors disabled:opacity-50"
              >
                <CheckCheck className="w-4 h-4" />
                <span>Aprovar compatíveis ({eligibleItems.length})</span>
              </button>
            )}

          </div>

          {/* SELECTION BAR (Aparece quando há itens selecionados para aprovação simultânea) */}
          {selectedItems.length > 0 && !batchProgress && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border-2 border-blue-500 bg-blue-50 p-3.5 shadow-md animate-in fade-in duration-200">
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                  {selectedItems.length}
                </span>
                <div>
                  <p className="text-sm font-bold text-blue-950">
                    {selectedItems.length} {selectedItems.length === 1 ? "baixa selecionada" : "baixas selecionadas"} para aprovação simultânea
                  </p>
                  <p className="text-xs text-blue-700">
                    Total selecionado: <strong className="font-semibold text-blue-900">{fmt(totalSelectedAmount)}</strong>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={busy || loading}
                  onClick={() => setSelectedKeys(new Set())}
                  className="flex items-center gap-1 rounded-lg border border-blue-300 bg-white px-3 py-1.5 text-xs font-semibold text-blue-800 hover:bg-blue-100 disabled:opacity-50 transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                  Desmarcar
                </button>

                <button
                  type="button"
                  disabled={busy || loading}
                  onClick={() => void handleBatchApprove(selectedItems, "SELECTED")}
                  className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                >
                  <CheckCheck className="h-4 w-4" />
                  Aprovar selecionados ({selectedItems.length})
                </button>
              </div>
            </div>
          )}

          {batchProgress && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-emerald-800">
                <span className="flex items-center gap-1.5">
                  <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
                  Aprovando baixas do saldo anterior em lote... ({batchProgress.current} de {batchProgress.total})
                </span>
                <span>{Math.round((batchProgress.current / batchProgress.total) * 100)}%</span>
              </div>
              <div className="w-full bg-emerald-200/60 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-emerald-600 h-2 rounded-full transition-all duration-150"
                  style={{ width: `${Math.round((batchProgress.current / batchProgress.total) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-emerald-700">
                Processando NF <strong>{batchProgress.currentNf}</strong> · Valor: <strong>{batchProgress.currentAmount}</strong>
              </p>
            </div>
          )}

          {/* LIST HEADER: SELECT ALL / ITEM COUNT */}
          {!loading && visibleItems.length > 0 && (
            <div className="flex items-center justify-between px-1 text-xs text-slate-500">
              <label className="flex items-center gap-2 cursor-pointer select-none font-medium hover:text-slate-800">
                <input
                  type="checkbox"
                  checked={allVisibleSelected}
                  onChange={toggleSelectAllVisible}
                  disabled={busy || loading}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                />
                <span>Selecionar todos ({visibleItems.length})</span>
              </label>

              <span>
                Exibindo {visibleItems.length} de {filtered.length} {filtered.length === 1 ? "sugestão" : "sugestões"}
              </span>
            </div>
          )}

          {!filtered.length && !loading && (
            <p className="text-sm text-slate-500">
              Nenhuma sugestao para este filtro.
            </p>
          )}

          {visibleItems.map(item => {
            const key = getItemKey(item);
            const isSelected = selectedKeys.has(key);
            const inv = rows[item.opening_index];
            const pay = paymentMap.get(item.payment_trans_id);

            return (

              <article
                key={key}
                className={`border rounded-xl p-4 space-y-3 transition-colors ${
                  isSelected ? "border-blue-500 bg-blue-50/20 shadow-xs ring-1 ring-blue-400" : ""
                }`}
              >

                <div className="flex flex-wrap justify-between items-center gap-2">

                  <div className="flex items-center gap-2.5">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={busy || loading}
                      onChange={() => toggleSelectItem(item)}
                      className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                      title="Selecionar para aprovação simultânea"
                    />
                    <b className="text-sm text-slate-800">{item.category.replace(/_/g, " ")}</b>
                  </div>

                  {item.ambiguous && (
                    <span className="text-amber-600 text-xs font-bold">
                      Multiplos candidatos
                    </span>
                  )}

                </div>

                <p className="text-xs">{item.reason}</p>

                {item.current_conflict && (
                  <p className="text-amber-600 text-xs">
                    Existe uma nota do exercicio atual que
                    tambem pode corresponder ao pagamento.
                  </p>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">

                  <div className="border rounded-lg p-3 space-y-1">

                    <p className="text-xs text-slate-500">
                      Provisao anterior
                    </p>

                    <b>NF {displayNf(item.opening_nf || inv?.extracted_nf, inv?.history)}</b>

                    <p className="text-xs">
                      {inv?.trans_date}
                    </p>

                    <p className="text-xs break-words">
                      {inv?.history}
                    </p>

                    <p className="font-bold">
                      {fmt(item.opening_amount)}
                    </p>

                  </div>

                  <div className="border rounded-lg p-3 space-y-1">

                    <p className="text-xs text-slate-500">
                      Pagamento atual
                    </p>

                    <b>NF {displayNf(item.payment_nf || pay?.extracted_nf, pay?.history)}</b>

                    <p className="text-xs">
                      {pay?.trans_date} | Linha {pay?.row_index}
                    </p>

                    <p className="text-xs break-words">
                      {pay?.history}
                    </p>

                    <p className="font-bold">
                      {fmt(item.payment_amount)}
                    </p>

                  </div>

                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">

                  <div>
                    <p className="text-xs">Baixa proposta</p>
                    <b>{fmt(Math.min(
                      Number(item.opening_amount),
                      Number(item.payment_amount)
                    ))}</b>
                  </div>

                  <div>
                    <p className="text-xs">Saldo da NF apos baixa</p>
                    <b>{fmt(item.opening_after)}</b>
                  </div>

                  <div>
                    <p className="text-xs">Pagamento residual</p>
                    <b>{fmt(item.payment_after)}</b>
                  </div>

                </div>

                <button
                  disabled={
                    busy ||
                    loading ||
                    !pay ||
                    !inv ||
                    !composition?.valid
                  }
                  onClick={() => void approve(item)}
                  className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 text-xs font-semibold disabled:opacity-40"
                >
                  {busy ? "Processando..." : "Aprovar baixa"}
                </button>

              </article>

            );

          })}

          {filtered.length > limit && (
            <button
              className="border rounded-lg px-4 py-2 text-sm"
              onClick={() => setLimit(v => v + 30)}
            >
              Mostrar mais sugestoes
            </button>
          )}

        </>

      )}

      <OpeningUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => {
          setIsUploadModalOpen(false);
          setSelectedUploadFile(null);
        }}
        jobId={jobId}
        initialBalance={initialBalance}
        initialFile={selectedUploadFile}
        onSuccess={async () => {
          await onRefresh();
          await load();
          setMessage("Planilha de Saldo Anterior importada e mapeada com sucesso!");
        }}
      />

    </section>
  );
}
