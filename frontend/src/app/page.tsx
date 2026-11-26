"use client";

import { useRef as useSyncRefV5 } from "react";
import {
    createRefreshCenterV5,
    fetchJobSnapshotV5,
    notifyRefreshV5
} from "@/lib/refresh-v5";


import SmartSuggestions from "@/components/SmartSuggestions";
import React, { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { Sidebar, NavTab } from "@/components/Sidebar";
import { Dashboard } from "@/components/Dashboard";
import { ReconciledTable } from "@/components/ReconciledTable";
import { OpenInvoicesTable } from "@/components/OpenInvoicesTable";
import { DivergencesTable } from "@/components/DivergencesTable";
import { ManualMatchModal } from "@/components/ManualMatchModal";
import { SupplierSummaryTable } from "@/components/SupplierSummaryTable";
import { BalanceCompositionTable } from "@/components/BalanceCompositionTable";
import { MathAuditModal } from "@/components/MathAuditModal";
import { UploadModal } from "@/components/UploadModal";
import { SettingsModal } from "@/components/SettingsModal";
import { api, deleteHistory } from "@/lib/api";
import { Loader2, AlertCircle, FileSpreadsheet, History as HistoryIcon } from "lucide-react";

export default function Home() {
  const [currentTab, setCurrentTab] = useState<NavTab>("dashboard");
  const [jobs, setJobs] = useState<any[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  
  // Data state
  const [jobSummary, setJobSummary] = useState<any>(null);
  const [reconciledItems, setReconciledItems] = useState<any[]>([]);
  const [openItems, setOpenItems] = useState<any[]>([]);
  const [divergencesData, setDivergencesData] = useState<{ divergent_pairs: any[]; unmapped_debits: any[] }>({
    divergent_pairs: [],
    unmapped_debits: []
  });
  const [supplierSummary, setSupplierSummary] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Load jobs list
  const loadJobs = async () => {
    try {
      setLoading(true);
      const list = await api.getJobs();
      setJobs(list);
      if (list.length > 0 && !activeJobId) {
        setActiveJobId(list[0].id);
      } else if (list.length === 0) {
        setLoading(false);
      }
    } catch (err: any) {
      setError("Erro ao carregar histórico: certifique-se de que o backend FastAPI está em execução na porta 8000.");
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const handleUploadSuccess = async (newJobId: string) => {
    await loadJobs();
    setActiveJobId(newJobId);
    setCurrentTab("dashboard");
  };




  // CONCILIA_V5_SAFE_REFRESH_23E

  const refreshCenterV5 = useSyncRefV5(
    createRefreshCenterV5()
  );

  const activeDocumentV5 = useSyncRefV5(activeJobId);

  activeDocumentV5.current = activeJobId;

  const [refreshRevisionV5, setRefreshRevisionV5] =
    useState(0);

  const refreshActiveJob = async () => {

    const id = activeJobId;

    if (!id || activeDocumentV5.current !== id) {
      return;
    }

    const center = refreshCenterV5.current;
    const ticket = center.begin(id);

    const isCurrent = () =>
      center.isCurrent(ticket) &&
      activeDocumentV5.current === id;

    try {

      const snapshot = await fetchJobSnapshotV5(id);

      if (!isCurrent()) return;

      setJobSummary(snapshot.summary);
      setReconciledItems(snapshot.reconciled);
      setOpenItems(snapshot.open);
      setDivergencesData(snapshot.divergences);
      setSupplierSummary(snapshot.suppliers);

      setError(null);

      setRefreshRevisionV5(v => v + 1);

      notifyRefreshV5(id, "snapshot");

    } catch (err) {

      if (!isCurrent()) return;

      throw err;

    } finally {

      if (isCurrent()) {
        setLoading(false);
      }

    }

  };

  useEffect(() => {

    const center = refreshCenterV5.current;

    center.invalidate();

    let cancelled = false;

    setJobSummary(null);
    setReconciledItems([]);
    setOpenItems([]);
    setDivergencesData({
      divergent_pairs: [],
      unmapped_debits: []
    });
    setSupplierSummary([]);

    setError(null);

    if (!activeJobId) {
      return;
    }

    setLoading(true);

    void refreshActiveJob().catch(err => {

      if (
        cancelled ||
        activeDocumentV5.current !== activeJobId
      ) return;

      setError(
        "Erro ao carregar dados: " +
        (err instanceof Error
          ? err.message
          : String(err))
      );

      setLoading(false);

    });

    return () => {

      cancelled = true;
      center.invalidate();

    };

  }, [activeJobId]);

  // CONCILIA_V5_MANUAL_UI_30A3C4A
  const handleManualMatchConfirm = async (
    invId: string,
    payId: string,
    expectedInvoiceRemaining: string,
    expectedPaymentRemaining: string
  ) => {
    const jobId = activeJobId;

    if (!jobId || activeDocumentV5.current !== jobId) {
      throw new Error(
        "Documento ativo alterado. Atualize os dados."
      );
    }

    const result = await api.manualMatch(
      jobId,
      invId,
      payId,
      "Conciliacao manual revisada pelo usuario.",
      {
        expected_invoice_remaining: expectedInvoiceRemaining,
        expected_payment_remaining: expectedPaymentRemaining,
        approval_source: "MANUAL",
        confirm_review: true
      }
    );

    if (!result.success) {
      throw new Error(
        result.detail || "Nao foi possivel concluir a baixa."
      );
    }

    try {
      await refreshActiveJob();
    } catch (err) {
      window.alert(
        "Baixa registrada, mas a tela nao foi atualizada. " +
        "Atualize os dados antes de continuar."
      );
    }
  };



  const [deleting, setDeleting] = useState(false);

  const removeHistory = async (id?: string) => {
    const message = id
      ? "Excluir este documento e sua conciliacao?"
      : "Excluir TODOS os documentos do historico?";
    if (!window.confirm(message)) return;

    setDeleting(true);
    try {
      await deleteHistory(id);
      window.location.reload();
    } catch (err: any) {
      window.alert(err.message);
    } finally {
      setDeleting(false);
    }
  };

  const counts = {
    reconciled: reconciledItems.length,
    open: openItems.length,
    divergences: (divergencesData?.divergent_pairs?.length || 0) + (divergencesData?.unmapped_debits?.length || 0),
    suppliers: supplierSummary.length,
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Header */}
      <Header
        job={jobSummary?.job?.id === activeJobId ? jobSummary.job : undefined}
        onOpenUpload={() => setIsUploadOpen(true)}
        onOpenAudit={() => setIsAuditOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />


      <div className="bg-white border-b border-slate-200 px-6 py-3 flex flex-wrap items-center gap-3">
        <label htmlFor="document-selector" className="text-xs font-bold text-slate-700">
          Documento selecionado
        </label>
        <select
          id="document-selector"
          value={activeJobId || ""}
          disabled={loading || deleting || jobs.length === 0}
          onChange={(e) => {
            refreshCenterV5.current.invalidate();
            activeDocumentV5.current = e.target.value;
            setJobSummary(null);
            setReconciledItems([]);
            setOpenItems([]);
            setDivergencesData({
              divergent_pairs: [],
              unmapped_debits: []
            });
            setSupplierSummary([]);
            setLoading(true);
            setActiveJobId(e.target.value);
            setCurrentTab("dashboard");
          }}
          className="flex-1 min-w-0 max-w-2xl border border-slate-300 rounded-lg px-3 py-2 text-sm bg-slate-50"
        >
          <option value="" disabled>Nenhum documento selecionado</option>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>
              {j.filename} - {j.company_name} - {j.period} - {new Date(j.created_at).toLocaleString("pt-BR")}
            </option>
          ))}
        </select>
        <span className="text-xs text-slate-500">
          {jobs.length} documento(s)
        </span>
        <button
          disabled={loading || deleting || !activeJobId}
          onClick={() => removeHistory(activeJobId || undefined)}
          className="border border-red-200 text-red-700 rounded-lg px-3 py-2 text-xs font-semibold disabled:opacity-40"
        >
          Excluir selecionado
        </button>
        <button
          disabled={loading || deleting || jobs.length === 0}
          onClick={() => removeHistory()}
          className="bg-red-600 hover:bg-red-700 text-white rounded-lg px-3 py-2 text-xs font-semibold disabled:opacity-40"
        >
          Limpar historico
        </button>
      </div>

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        {/* Left Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onSelectTab={setCurrentTab}
          counts={counts}
        />

        {/* Main Content Area */}
        <main className="flex-1 p-6 overflow-y-auto">
          {!loading && !error && activeJobId && jobSummary?.job?.id === activeJobId && (
            <div className="flex justify-end mb-4">
              <a href={api.getTabExportUrl(activeJobId,currentTab)} className="inline-flex items-center gap-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg px-4 py-2 text-sm font-semibold"><FileSpreadsheet className="w-4 h-4"/>Exportar esta aba (Excel)</a>
            </div>
          )}
          {loading ? (
            <div className="h-96 flex flex-col items-center justify-center space-y-3 text-slate-500">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              <p className="text-xs font-medium">Carregando auditoria contábil...</p>
            </div>
          ) : error ? (
            <div className="p-6 rounded-xl bg-white border border-rose-200 shadow-sm text-center space-y-3">
              <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
              <h3 className="text-base font-bold text-slate-900">Atenção ao Conectar Backend</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">{error}</p>
              <button
                onClick={() => setIsUploadOpen(true)}
                className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg shadow hover:bg-blue-500 transition"
              >
                Importar Arquivo Razão.xls
              </button>
            </div>
          ) : !activeJobId ? (
            /* Empty State */
            <div className="h-96 flex flex-col items-center justify-center space-y-4 text-center p-8 bg-white rounded-2xl border border-slate-200 shadow-sm">
              <FileSpreadsheet className="w-12 h-12 text-blue-500" />
              <div>
                <h3 className="text-base font-bold text-slate-900">Nenhum Razão Contábil Importado</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  Envie o arquivo Razão.xls ou qualquer planilha de razão contábil para iniciar a conciliação automática.
                </p>
              </div>
              <button
                onClick={() => setIsUploadOpen(true)}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow transition"
              >
                Importar Razão Contábil Agora
              </button>
            </div>
          ) : (
            /* Views by Tab */
            <>
              {currentTab === "dashboard" && (
                <Dashboard
                  summary={jobSummary?.summary}
                  job={jobSummary?.job}
                  mathAudit={jobSummary?.math_audit}
                  monthlyEvolution={jobSummary?.monthly_evolution || []}
                  onOpenAudit={() => setIsAuditOpen(true)}
                  onNavigateTab={(t: NavTab) => setCurrentTab(t)}
                />
              )}

              {currentTab === "composition" && (
                <BalanceCompositionTable
                  key={activeJobId}
                  onRefresh={refreshActiveJob}
                  revision={refreshRevisionV5}
                  job={jobSummary?.job}
                  summary={jobSummary?.summary}
                  openItems={openItems}
                  divergentItems={divergencesData?.divergent_pairs || []}
                  onOpenAudit={() => setIsAuditOpen(true)}
                />
              )}

              {currentTab === "reconciled" && (
                <ReconciledTable items={reconciledItems} />
              )}

              {currentTab === "open" && (
                <OpenInvoicesTable items={openItems} />
              )}

              {currentTab === "divergences" && (
                <DivergencesTable
                  divergentPairs={divergencesData?.divergent_pairs || []}
                  unmappedDebits={divergencesData?.unmapped_debits || []}
                />
              )}

              {currentTab === "manual" && (
                
    <div className="space-y-6">
        {activeJobId && (
            <SmartSuggestions
                revision={refreshRevisionV5}
                key={activeJobId}
                jobId={activeJobId}
                onRefresh={refreshActiveJob}
            />
        )}
        <details className="rounded-2xl border border-slate-200 bg-white p-5">
            <summary className="cursor-pointer font-bold text-slate-700">
                Abrir conciliacao manual tradicional
            </summary>
            <div className="mt-5">
                <ManualMatchModal
                  openInvoices={openItems}
                  unmappedPayments={divergencesData?.unmapped_debits || []}
                  onConfirmMatch={handleManualMatchConfirm}
                />
            </div>
        </details>
    </div>

              )}

              {currentTab === "suppliers" && (
                <SupplierSummaryTable items={supplierSummary} />
              )}

              {currentTab === "history" && (
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                  <div className="flex items-center space-x-2 border-b border-slate-200 pb-3">
                    <HistoryIcon className="w-5 h-5 text-blue-600" />
                    <h3 className="text-base font-bold text-slate-900">Histórico de Arquivos Processados</h3>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {jobs.map((j) => (
                      <div
                        key={j.id}
                        onClick={() => setActiveJobId(j.id)}
                        className={`p-4 rounded-lg flex items-center justify-between cursor-pointer transition ${
                          activeJobId === j.id
                            ? "bg-blue-50/70 border border-blue-200"
                            : "hover:bg-slate-50"
                        }`}
                      >
                        <div>
                          <p className="font-bold text-sm text-slate-900">{j.filename}</p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {j.company_name} • {j.period} • CNPJ: {j.cnpj}
                          </p>
                          <p className="text-[11px] text-slate-400 mt-1">
                            Processado em: {new Date(j.created_at).toLocaleString("pt-BR")}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-mono font-bold text-slate-900 block">
                            Saldo: R$ {parseFloat(j.final_reported_balance || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                          </span>
                          <span className="inline-block mt-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                            {activeJobId === j.id ? "Selecionado" : j.status}
                          </span>
                          <button
                            disabled={loading || deleting}
                            onClick={(e) => {
                              e.stopPropagation();
                              removeHistory(j.id);
                            }}
                            className="block ml-auto mt-2 text-xs font-semibold text-red-600 hover:underline"
                          >
                            Excluir documento
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Math Audit Modal */}
      <MathAuditModal
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
        mathAudit={jobSummary?.math_audit}
        job={jobSummary?.job}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        activeJobId={activeJobId}
        onSettingsSaved={async () => {
          // CONCILIA_V5_SETTINGS_REFRESH_29C
          if (activeJobId) {
            try {
              await refreshActiveJob();
            } catch (err: any) {
              setError(
                err?.message ||
                "Nao foi possivel atualizar o documento."
              );
              throw err;
            }
          }
        }}
      />
    </div>
  );
}
