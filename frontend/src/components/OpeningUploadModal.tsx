"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  X,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  ArrowRight,
  Loader2,
  ShieldCheck,
  Check
} from "lucide-react";
import {
  previewOpeningV5,
  validateOpeningV5,
  attachOpening,
  type OpeningPreviewV5,
  type OpeningValidationV5
} from "@/lib/api";

interface OpeningUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  initialBalance?: string;
  initialFile?: File | null;
  onSuccess: () => Promise<void> | void;
}

const OPENING_FIELDS: {
  key: "date" | "value" | "history" | "nf" | "supplier" | "nature";
  label: string;
  required: boolean;
  hint: string;
}[] = [
  { key: "date", label: "Data do título / emissão", required: true, hint: "Coluna com a data do título" },
  { key: "value", label: "Valor / Saldo em aberto", required: true, hint: "Coluna com o valor a comprovar" },
  { key: "history", label: "Histórico / Descrição", required: true, hint: "Coluna com o histórico ou descrição" },
  { key: "nf", label: "Número da NF", required: false, hint: "Opcional: extraído da descrição se ausente" },
  { key: "supplier", label: "Fornecedor", required: false, hint: "Opcional: extraído da descrição se ausente" },
  { key: "nature", label: "Natureza (D / C)", required: false, hint: "Opcional: padrão Crédito/A pagar" }
];

const money = (value: string | number) =>
  Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });

export const OpeningUploadModal: React.FC<OpeningUploadModalProps> = ({
  isOpen,
  onClose,
  jobId,
  initialBalance,
  initialFile,
  onSuccess
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState(0);

  const [preview, setPreview] = useState<OpeningPreviewV5 | null>(null);
  const [mapping, setMapping] = useState<Record<string, number>>({});
  const [headerRow, setHeaderRow] = useState<number>(0);
  const [validation, setValidation] = useState<OpeningValidationV5 | null>(null);

  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const request = useRef<AbortController | null>(null);
  const locked = useRef(false);

  useEffect(() => {
    if (isOpen) {
      if (initialFile) {
        setFile(initialFile);
        void handleInspect(initialFile);
      } else {
        setStep(0);
        setFile(null);
        setPreview(null);
        setValidation(null);
        setError("");
      }
    } else {
      request.current?.abort();
      setFile(null);
      setStep(0);
      setPreview(null);
      setValidation(null);
      setError("");
    }
  }, [isOpen, initialFile]);

  const handleInspect = async (selectedFile: File, customHeader?: number) => {
    if (!selectedFile || locked.current) return;
    locked.current = true;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;

    setBusy("Analisando estrutura da planilha de saldo anterior...");
    setError("");

    try {
      const res = await previewOpeningV5(
        jobId,
        selectedFile,
        typeof customHeader === "number" ? customHeader : undefined,
        controller.signal
      );

      setPreview(res);
      setHeaderRow(res.header_row);

      const preMapped: Record<string, number> = {};
      for (const f of OPENING_FIELDS) {
        if (typeof res.mapping[f.key] === "number") {
          preMapped[f.key] = res.mapping[f.key];
        }
      }
      setMapping(preMapped);
      setStep(1);
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setError(err.message || "Erro ao ler a planilha.");
      }
    } finally {
      locked.current = false;
      setBusy("");
    }
  };

  const handleChooseFile = (selected: File | null) => {
    if (!selected) return;
    setFile(selected);
    void handleInspect(selected);
  };

  const changeColumn = (field: string, valStr: string) => {
    setValidation(null);
    if (valStr === "") {
      const next = { ...mapping };
      delete next[field];
      setMapping(next);
    } else {
      setMapping(prev => ({
        ...prev,
        [field]: Number(valStr)
      }));
    }
  };

  const isMappingValid = () => {
    if (typeof mapping.date !== "number") return false;
    if (typeof mapping.value !== "number") return false;
    if (typeof mapping.history !== "number") return false;

    // Check for duplicates among assigned columns
    const assigned = Object.values(mapping).filter(v => typeof v === "number");
    const unique = new Set(assigned).size === assigned.length;
    return unique;
  };

  const handleValidate = async () => {
    if (!file || !isMappingValid() || locked.current) return;
    locked.current = true;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;

    setBusy("Validando títulos do saldo anterior...");
    setError("");

    try {
      const res = await validateOpeningV5(
        jobId,
        file,
        headerRow,
        mapping,
        controller.signal
      );
      setValidation(res);
      setStep(2);
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setError(err.message || "Erro ao validar planilha.");
      }
    } finally {
      locked.current = false;
      setBusy("");
    }
  };

  const handleConfirm = async () => {
    if (!file || !validation || locked.current) return;
    locked.current = true;
    setBusy("Gravando lançamentos de saldo anterior...");
    setError("");

    try {
      await attachOpening(jobId, file, headerRow, mapping);
      await onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Erro ao confirmar importação do saldo anterior.");
    } finally {
      locked.current = false;
      setBusy("");
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4"
    >
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full flex flex-col max-h-[90vh] overflow-hidden border border-slate-200">
        {/* Header */}
        <header className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
              <UploadCloud className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-800">
                Importar Saldo Anterior do Fornecedor
              </h2>
              <p className="text-xs text-slate-500">
                Concilia AI · Conciliação de Exercícios Anteriores
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={!!busy}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 disabled:opacity-40 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </header>

        {/* Wizard Steps indicator */}
        <div className="grid grid-cols-3 gap-3 px-6 pt-4">
          {["Selecionar planilha", "Mapear colunas", "Validar e anexar"].map((label, index) => (
            <div key={label}>
              <div
                className={`h-1.5 rounded-full mb-1.5 transition-colors ${
                  index <= step ? "bg-blue-600" : "bg-slate-200"
                }`}
              />
              <p
                className={`text-xs font-semibold ${
                  index === step ? "text-blue-700 font-bold" : "text-slate-500"
                }`}
              >
                {index + 1}. {label}
              </p>
            </div>
          ))}
        </div>

        {/* Content body */}
        <main className="overflow-y-auto p-6 space-y-4 flex-1">
          {error && (
            <div
              role="alert"
              className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex gap-2.5 items-start"
            >
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
              <div className="flex-1">
                <p className="font-semibold text-rose-900">Atenção ao importar</p>
                <p className="text-xs text-rose-700 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {/* STEP 0: Select File */}
          {step === 0 && (
            <div className="space-y-4">
              <label
                className="relative block border-2 border-dashed border-slate-300 rounded-2xl p-10 text-center bg-slate-50 hover:border-blue-500 cursor-pointer transition-colors"
                onDragOver={e => e.preventDefault()}
                onDrop={e => {
                  e.preventDefault();
                  const f = e.dataTransfer.files?.[0];
                  if (f) handleChooseFile(f);
                }}
              >
                <input
                  type="file"
                  accept=".xls,.xlsx,.csv"
                  disabled={!!busy}
                  onChange={e => {
                    const f = e.target.files?.[0];
                    if (f) handleChooseFile(f);
                    e.target.value = "";
                  }}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <FileSpreadsheet className="w-12 h-12 mx-auto text-blue-600 mb-3" />
                <p className="font-bold text-slate-800 text-base">
                  {file ? file.name : "Clique para selecionar ou arraste a planilha de saldo anterior"}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Formatos aceitos: Excel (.xlsx, .xls) ou CSV com títulos a pagar de exercícios anteriores.
                </p>
              </label>

              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex gap-3 text-xs text-blue-800">
                <ShieldCheck className="w-5 h-5 shrink-0 text-blue-600" />
                <p>
                  A planilha será analisada e mapeada na próxima etapa. Você poderá conferir todos os valores e linhas antes da confirmação final.
                </p>
              </div>
            </div>
          )}

          {/* STEP 1: Column Mapping */}
          {step === 1 && preview && (
            <div className="space-y-4">
              <div className="flex flex-wrap justify-between items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl p-3">
                <div>
                  <p className="font-bold text-slate-800 text-sm break-all">{file?.name}</p>
                  <p className="text-xs text-slate-500">
                    {preview.row_count} linhas · {preview.column_count} colunas identificadas
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setStep(0)}
                  disabled={!!busy}
                  className="text-xs text-blue-600 hover:text-blue-800 font-semibold"
                >
                  Trocar arquivo
                </button>
              </div>

              {/* Header Row selector */}
              <div className="flex flex-wrap items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl p-3">
                <label className="text-xs font-semibold text-slate-700">
                  Linha do cabeçalho na planilha:
                  <select
                    value={headerRow}
                    disabled={!!busy}
                    onChange={e => {
                      const val = Number(e.target.value);
                      setHeaderRow(val);
                      if (file) void handleInspect(file, val);
                    }}
                    className="ml-2 border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-xs font-normal"
                  >
                    <option value={0}>Sem cabeçalho (dados iniciam na linha 1)</option>
                    {Array.from({ length: Math.min(10, preview.row_count) }, (_, i) => i + 1).map(num => (
                      <option key={num} value={num}>
                        Linha {num} {num === 1 ? "(padrão)" : ""}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="text-[11px] text-slate-500">
                  Se a planilha não possui títulos de coluna, selecione &quot;Sem cabeçalho&quot;.
                </p>
              </div>

              {/* Mapping Fields */}
              <div>
                <p className="text-xs font-bold text-slate-700 mb-2">
                  Mapeamento dos campos contábeis:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {OPENING_FIELDS.map(f => (
                    <label key={f.key} className="block text-xs font-medium text-slate-700">
                      <span className="flex items-center justify-between">
                        <span>
                          {f.label} {f.required && <span className="text-rose-500 font-bold">*</span>}
                        </span>
                        <span className="text-[10px] text-slate-400 font-normal">
                          {f.required ? "Obrigatório" : "Opcional"}
                        </span>
                      </span>
                      <select
                        value={mapping[f.key] ?? ""}
                        disabled={!!busy}
                        onChange={e => changeColumn(f.key, e.target.value)}
                        className={`block w-full mt-1 border rounded-xl px-3 py-2 text-xs bg-white ${
                          f.required && typeof mapping[f.key] !== "number"
                            ? "border-amber-300 bg-amber-50/30"
                            : "border-slate-300"
                        }`}
                      >
                        <option value="">
                          {f.required ? "-- Selecione a coluna --" : "(Nenhuma / Extrair do Histórico)"}
                        </option>
                        {preview.columns.map(col => (
                          <option key={col.index} value={col.index}>
                            Coluna {col.letter} {col.header ? `(${col.header})` : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
              </div>

              {/* Table Data Preview */}
              <div>
                <p className="text-xs font-bold text-slate-700 mb-1.5">
                  Pré-visualização das primeiras linhas da sua planilha:
                </p>
                <div className="border border-slate-200 rounded-xl overflow-x-auto max-h-48">
                  <table className="w-full text-[11px] text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                        {preview.columns.map(col => (
                          <th key={col.index} className="p-2 border-r border-slate-200 whitespace-nowrap">
                            Coluna {col.letter}
                            {col.header && <span className="block text-[10px] text-slate-500 font-normal">{col.header}</span>}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.sample_rows.map((rowVals, rIdx) => (
                        <tr key={rIdx} className="border-b border-slate-100 hover:bg-slate-50">
                          {rowVals.map((val, cIdx) => (
                            <td key={cIdx} className="p-2 border-r border-slate-100 text-slate-600 truncate max-w-[200px]">
                              {val}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Validate and Confirm */}
          {step === 2 && validation && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-center gap-3">
                <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                <div>
                  <p className="font-bold text-emerald-900 text-sm">
                    Validação do Saldo Anterior Concluída com Sucesso!
                  </p>
                  <p className="text-xs text-emerald-700">
                    Confira o resumo financeiro dos títulos identificados antes de gravar.
                  </p>
                </div>
              </div>

              {/* Financial comparison cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-center">
                  <p className="text-[11px] text-slate-500 font-medium">Títulos Lidos</p>
                  <p className="text-base font-bold text-slate-800 mt-1">{validation.count}</p>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-center">
                  <p className="text-[11px] text-slate-500 font-medium">Total da Planilha</p>
                  <p className="text-base font-bold text-blue-700 mt-1">
                    {money(validation.total_amount)}
                  </p>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-center">
                  <p className="text-[11px] text-slate-500 font-medium">Saldo Razão</p>
                  <p className="text-base font-bold text-slate-800 mt-1">
                    {money(validation.job_initial_balance)}
                  </p>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-center">
                  <p className="text-[11px] text-slate-500 font-medium">Diferença</p>
                  <p
                    className={`text-base font-bold mt-1 ${
                      Number(validation.difference) === 0 ? "text-emerald-600" : "text-amber-600"
                    }`}
                  >
                    {money(validation.difference)}
                  </p>
                </div>
              </div>

              {/* Parsed rows preview */}
              <div>
                <p className="text-xs font-bold text-slate-700 mb-1.5">
                  Lançamentos identificados prontos para cruzamento:
                </p>
                <div className="border border-slate-200 rounded-xl overflow-x-auto max-h-52">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                        <th className="p-2.5">Data</th>
                        <th className="p-2.5">NF</th>
                        <th className="p-2.5">Histórico / Fornecedor</th>
                        <th className="p-2.5 text-right">Valor Nominal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {validation.sample.map((row, idx) => (
                        <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="p-2.5 text-slate-600 font-mono text-[11px]">{row.trans_date}</td>
                          <td className="p-2.5 font-bold text-blue-700">{row.extracted_nf || "S/N"}</td>
                          <td className="p-2.5 text-slate-700 truncate max-w-xs">{row.history}</td>
                          <td className="p-2.5 text-right font-bold text-slate-800">
                            {money(Math.abs(Number(row.value)))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </main>

        {/* Footer actions */}
        <footer className="px-6 py-4 border-t border-slate-100 flex justify-between items-center bg-slate-50/60">
          <div>
            {step === 1 && (
              <button
                type="button"
                onClick={() => setStep(0)}
                disabled={!!busy}
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold hover:bg-slate-100 disabled:opacity-40 inline-flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Voltar
              </button>
            )}
            {step === 2 && (
              <button
                type="button"
                onClick={() => setStep(1)}
                disabled={!!busy}
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold hover:bg-slate-100 disabled:opacity-40 inline-flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Ajustar mapeamento
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={!!busy}
              className="px-4 py-2 rounded-xl text-slate-600 text-xs font-semibold hover:bg-slate-100 disabled:opacity-40"
            >
              Cancelar
            </button>

            {step === 1 && (
              <button
                type="button"
                onClick={handleValidate}
                disabled={!!busy || !isMappingValid()}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold disabled:opacity-40 inline-flex items-center gap-2 shadow-sm"
              >
                {busy ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Validando...</span>
                  </>
                ) : (
                  <>
                    <span>Avançar para validação</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            )}

            {step === 2 && (
              <button
                type="button"
                onClick={handleConfirm}
                disabled={!!busy}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold disabled:opacity-40 inline-flex items-center gap-2 shadow-sm"
              >
                {busy ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Gravando...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Confirmar e Conciliar Saldo Anterior</span>
                  </>
                )}
              </button>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
};
