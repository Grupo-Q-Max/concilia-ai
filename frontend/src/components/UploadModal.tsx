
"use client";

// CONCILIA_V5_UPLOAD_WIZARD_29D42

import React, {
  useState,
  useRef,
  useEffect
} from "react";

import {
  UploadCloud,
  FileSpreadsheet,
  X,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  ArrowRight,
  Loader2,
  ShieldCheck
} from "lucide-react";

import {
  api,
  type ImportFieldV5,
  type ImportMappingV5,
  type ImportPreviewV5,
  type ImportValidationV5
} from "@/lib/api";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (jobId: string) => void;
}

const FIELDS: {
  key: ImportFieldV5;
  label: string;
}[] = [
  { key: "date", label: "Data do lançamento" },
  { key: "history", label: "Histórico" },
  { key: "debit", label: "Débito" },
  { key: "credit", label: "Crédito" },
  { key: "balance", label: "Saldo acumulado / exercício" }
];

const money = (value: string) =>
  Number(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });

const balance = (value: string) => {
  const number = Number(value);

  return money(String(Math.abs(number))) +
    (number < 0 ? " C" : number > 0 ? " D" : "");
};

const primary =
  "px-5 py-2.5 rounded-xl bg-blue-600 " +
  "hover:bg-blue-700 text-white text-sm font-semibold " +
  "disabled:opacity-40 disabled:cursor-not-allowed " +
  "inline-flex items-center justify-center gap-2";

const secondary =
  "px-4 py-2.5 rounded-xl border border-slate-200 " +
  "text-slate-600 text-sm font-semibold " +
  "hover:bg-slate-50 disabled:opacity-40";

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess
}) => {

  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState(0);

  const [preview, setPreview] =
    useState<ImportPreviewV5 | null>(null);

  const [mapping, setMapping] =
    useState<ImportMappingV5>({});

  const [headerRow, setHeaderRow] = useState(1);

  const [validation, setValidation] =
    useState<ImportValidationV5 | null>(null);

  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const request = useRef<AbortController | null>(null);
  const locked = useRef(false);

  useEffect(() => {

    if (!isOpen && !locked.current) {
      request.current?.abort();

      setFile(null);
      setStep(0);
      setPreview(null);
      setMapping({});
      setHeaderRow(1);
      setValidation(null);
      setBusy("");
      setError("");
    }

    return () => {
      request.current?.abort();
    };

  }, [isOpen]);

  const complete = FIELDS.every(
    field => Number.isInteger(mapping[field.key])
  );

  const indexes = Object.values(mapping);

  const unique =
    new Set(indexes).size === indexes.length;

  const inRange = indexes.every(
    index =>
      Number.isInteger(index) &&
      index >= 0 &&
      index < (preview?.column_count ?? 0)
  );

  const headerValid =
    Number.isInteger(headerRow) &&
    headerRow >= 1 &&
    headerRow < (preview?.row_count ?? 0);

  const mappingValid =
    complete && unique && inRange && headerValid;

  const close = () => {

    if (locked.current) return;

    request.current?.abort();
    onClose();
  };

  const chooseFile = (selected: File | null) => {

    if (locked.current) return;

    request.current?.abort();

    setFile(null);
    setPreview(null);
    setValidation(null);
    setMapping({});
    setStep(0);
    setHeaderRow(1);
    setError("");

    if (!selected) return;

    if (selected.size === 0) {
      setError("A planilha está vazia.");
      return;
    }

    if (selected.size > 50 * 1024 * 1024) {
      setError("A planilha ultrapassa 50 MB.");
      return;
    }

    setFile(selected);
  };

  const inspect = async (customHeader?: number) => {

    if (!file || locked.current) return;

    locked.current = true;

    request.current?.abort();

    const controller = new AbortController();

    request.current = controller;

    setBusy("Analisando planilha...");
    setError("");
    setValidation(null);

    try {

      const result = await api.previewImportV5(
        file,
        customHeader,
        controller.signal
      );

      if (controller.signal.aborted) return;

      setPreview(result);
      setHeaderRow(result.header_row + 1);

      const detected = result.automatic_mapping;

      if (
        detected &&
        detected.header_row === result.header_row
      ) {
        const selected: ImportMappingV5 = {};

        FIELDS.forEach(field => {
          const index = detected.mapping[field.key];

          if (typeof index === "number") {
            selected[field.key] = index;
          }
        });

        setMapping(selected);

      } else {
        setMapping({});
      }

      setStep(1);

    } catch (err) {

      if (!controller.signal.aborted) {
        setError(
          err instanceof Error
            ? err.message
            : "Não foi possível analisar a planilha."
        );
      }

    } finally {
      locked.current = false;
      setBusy("");
    }
  };

  const changeColumn = (
    field: ImportFieldV5,
    value: string
  ) => {

    setValidation(null);
    setError("");

    setMapping(old => {

      const next = { ...old };

      if (value === "") {
        delete next[field];
      } else {
        next[field] = Number(value);
      }

      return next;
    });
  };

  const validate = async () => {

    if (
      !file ||
      !preview ||
      !mappingValid ||
      locked.current
    ) return;

    if (headerRow - 1 !== preview.header_row) {
      setError(
        "Atualize a prévia do cabeçalho antes de validar."
      );
      return;
    }

    locked.current = true;

    request.current?.abort();

    const controller = new AbortController();

    request.current = controller;

    setBusy("Validando contabilidade...");
    setValidation(null);
    setError("");

    try {

      const result = await api.validateImportV5(
        file,
        headerRow - 1,
        mapping,
        controller.signal
      );

      if (controller.signal.aborted) return;

      if (result.file_hash !== preview.file_hash) {
        throw new Error(
          "O arquivo foi alterado. Gere uma nova prévia."
        );
      }

      setValidation(result);
      setStep(2);

    } catch (err) {

      if (!controller.signal.aborted) {
        setError(
          err instanceof Error
            ? err.message
            : "Erro na validação contábil."
        );
      }

    } finally {
      locked.current = false;
      setBusy("");
    }
  };

  const confirm = async () => {

    if (
      !file ||
      !validation?.valid ||
      locked.current
    ) return;

    locked.current = true;

    setBusy("Importando e conciliando...");
    setError("");

    let importedJob: string | null = null;

    try {

      const result = await api.confirmImportV5(
        file,
        validation
      );

      importedJob = result.job_id;

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Erro ao importar o documento."
      );

    } finally {

      locked.current = false;
      setBusy("");
    }

    if (importedJob) {
      setValidation(null);
      onClose();
      onUploadSuccess(importedJob);
    }
  };

  if (!isOpen) return null;

  const approved =
    validation?.valid === true &&
    validation.audit_status === "VALID" &&
    Number(validation.difference) === 0;

  return (

    <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6">

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Importar Razão Contábil"
        className="bg-white rounded-2xl w-full max-w-5xl max-h-[94vh] shadow-2xl flex flex-col overflow-hidden"
      >

        <header className="bg-slate-900 p-5 border-b border-slate-200 flex items-center justify-between gap-3">

          <div className="flex items-center gap-3">

            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
              <UploadCloud className="w-6 h-6" />
            </div>

            <div>
              <h2 className="font-bold text-lg text-white">
                Importar Razão Contábil
              </h2>

              <p className="text-xs text-slate-200">
                Concilia AI V5 Professional
              </p>
            </div>

          </div>

          <button
            onClick={close}
            disabled={!!busy}
            aria-label="Fechar importador"
            className="p-2 text-slate-200 hover:text-white disabled:opacity-30"
          >
            <X className="w-5 h-5" />
          </button>

        </header>

        <div className="grid grid-cols-3 gap-3 px-5 pt-5">

          {[
            "Selecionar arquivo",
            "Mapear colunas",
            "Validar e importar"
          ].map((label, index) => (

            <div key={label}>

              <div className={
                "h-1.5 rounded-full mb-2 " +
                (index <= step
                  ? "bg-blue-600"
                  : "bg-slate-200")
              } />

              <p className={
                "text-xs font-semibold " +
                (index === step
                  ? "text-blue-700"
                  : "text-slate-500")
              }>
                {index + 1}. {label}
              </p>

            </div>

          ))}

        </div>

        <main className="overflow-y-auto p-5 space-y-5 flex-1">

          {error && (

            <div
              role="alert"
              className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex gap-2"
            >
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>

          )}

          {step === 0 && (

            <>

              <label
                className="relative block border-2 border-dashed border-slate-300 rounded-2xl p-12 text-center bg-slate-50 hover:border-blue-500 cursor-pointer"
                onDragOver={event => event.preventDefault()}
                onDrop={event => {
                  event.preventDefault();
                  chooseFile(
                    event.dataTransfer.files[0] || null
                  );
                }}
              >

                <input
                  type="file"
                  accept=".xls,.xlsx,.xlsm,.xlsb,.csv,.html,.htm,.xml"
                  disabled={!!busy}
                  onChange={event => chooseFile(
                    event.target.files?.[0] || null
                  )}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />

                <FileSpreadsheet className="w-12 h-12 mx-auto text-emerald-600 mb-4" />

                <p className="font-bold text-slate-800 break-all">
                  {file
                    ? file.name
                    : "Selecione ou arraste sua planilha"}
                </p>

                <p className="text-sm text-slate-500 mt-2">
                  {file
                    ? `${(file.size / 1024).toFixed(1)} KB`
                    : "Excel ou CSV — até 50 MB"}
                </p>

              </label>

              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex gap-3 text-sm text-blue-800">

                <ShieldCheck className="w-5 h-5 shrink-0" />

                <p>
                  A planilha será analisada antes da
                  importação. Nenhum lançamento será
                  gravado até a confirmação.
                </p>

              </div>

            </>

          )}

          {step === 1 && preview && (

            <>

              <div className="flex flex-wrap justify-between items-center gap-3">

                <div>
                  <p className="font-bold text-slate-800 break-all">
                    {file?.name}
                  </p>

                  <p className="text-xs text-slate-500">
                    {preview.row_count} linhas ·
                    {" "}{preview.column_count} colunas
                  </p>
                </div>

                <span className={
                  "px-3 py-1.5 rounded-lg text-xs font-semibold " +
                  (preview.requires_manual_mapping
                    ? "bg-amber-50 text-amber-800"
                    : "bg-emerald-50 text-emerald-800")
                }>
                  {preview.requires_manual_mapping
                    ? "Mapeamento personalizado"
                    : "Layout reconhecido"}
                </span>

              </div>

              <div className="flex flex-wrap items-end gap-3 bg-slate-50 border border-slate-200 rounded-xl p-4">

                <label className="text-sm font-medium text-slate-700">

                  Linha do cabeçalho

                  <input
                    type="number"
                    min={1}
                    max={preview.row_count - 1}
                    value={headerRow}
                    disabled={!!busy}
                    onChange={event => {
                      setHeaderRow(Number(event.target.value));
                      setValidation(null);
                    }}
                    className="block mt-1 w-28 border border-slate-300 rounded-lg px-3 py-2 bg-white"
                  />

                </label>

                <button
                  className={secondary}
                  disabled={!!busy || !headerValid}
                  onClick={() => inspect(headerRow - 1)}
                >
                  Atualizar prévia
                </button>

                <p className="text-xs text-slate-500">
                  Informe o número da linha no Excel.
                </p>

              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

                {FIELDS.map(field => (

                  <label
                    key={field.key}
                    className="block text-sm font-semibold text-slate-700"
                  >

                    {field.label}

                    <select
                      disabled={!!busy}
                      value={mapping[field.key] ?? ""}
                      onChange={event => changeColumn(
                        field.key,
                        event.target.value
                      )}
                      className="block w-full mt-1 border border-slate-300 bg-white rounded-xl px-3 py-2.5 text-sm"
                    >

                      <option value="">
                        Selecione a coluna
                      </option>

                      {preview.columns.map(column => (

                        <option
                          key={column.index}
                          value={column.index}
                        >
                          {column.letter} — {column.header || "(sem título)"}
                        </option>

                      ))}

                    </select>

                  </label>

                ))}

              </div>

              {!unique && (

                <p className="text-sm font-semibold text-rose-700">
                  Uma mesma coluna não pode ser utilizada
                  em dois campos.
                </p>

              )}

              <div>

                <h3 className="font-bold text-slate-800 mb-2">
                  Prévia da planilha
                </h3>

                <div className="overflow-auto max-h-64 rounded-xl border border-slate-200">

                  <table className="w-full text-xs whitespace-nowrap">

                    <thead className="sticky top-0 bg-slate-100 text-slate-700">

                      <tr>
                        <th className="p-3 text-left">Linha</th>

                        {preview.columns.map(column => (

                          <th
                            key={column.index}
                            className="p-3 text-left"
                          >
                            {column.letter} — {column.header}
                          </th>

                        ))}

                      </tr>

                    </thead>

                    <tbody>

                      {preview.sample.map(row => (

                        <tr
                          key={row.row}
                          className="border-t border-slate-100"
                        >

                          <td className="p-3 text-slate-500">
                            {row.row}
                          </td>

                          {row.values.map((value, index) => (

                            <td
                              key={index}
                              title={value}
                              className="p-3 max-w-[260px] truncate text-slate-700"
                            >
                              {value || "—"}
                            </td>

                          ))}

                        </tr>

                      ))}

                    </tbody>

                  </table>

                </div>

              </div>

            </>

          )}

          {step === 2 && validation && (

            <>

              <div className={
                "rounded-xl border p-5 flex items-center gap-3 " +
                (approved
                  ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                  : "bg-rose-50 border-rose-200 text-rose-800")
              }>

                {approved
                  ? <CheckCircle2 className="w-8 h-8 shrink-0" />
                  : <AlertCircle className="w-8 h-8 shrink-0" />}

                <div>

                  <h3 className="font-bold">
                    {approved
                      ? "Validação contábil aprovada"
                      : "Divergência contábil identificada"}
                  </h3>

                  <p className="text-sm mt-1">
                    {approved
                      ? "Confira os valores e confirme a importação."
                      : "Revise o cabeçalho e o mapeamento das colunas."}
                  </p>

                </div>

              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">

                {[
                  {
                    label: "Lançamentos",
                    value: String(validation.transaction_count)
                  },
                  {
                    label: "Saldo anterior",
                    value: balance(validation.initial_balance)
                  },
                  {
                    label: "Total de débitos",
                    value: money(validation.total_debits)
                  },
                  {
                    label: "Total de créditos",
                    value: money(validation.total_credits)
                  },
                  {
                    label: "Saldo calculado",
                    value: balance(validation.calculated_balance)
                  },
                  {
                    label: "Saldo informado",
                    value: balance(validation.reported_balance)
                  }
                ].map(item => (

                  <div
                    key={item.label}
                    className="border border-slate-200 rounded-xl p-4"
                  >

                    <p className="text-xs text-slate-500">
                      {item.label}
                    </p>

                    <p className="text-lg font-bold text-slate-900 mt-2 tabular-nums">
                      {item.value}
                    </p>

                  </div>

                ))}

              </div>

              <div className="border border-slate-200 rounded-xl p-5 flex flex-wrap justify-between items-center gap-3">

                <div>

                  <p className="font-semibold text-slate-700">
                    Diferença contábil
                  </p>

                  <p className="text-xs text-slate-500 mt-1">
                    Saldo calculado menos saldo informado
                  </p>

                </div>

                <p className={
                  "text-2xl font-bold tabular-nums " +
                  (approved
                    ? "text-emerald-700"
                    : "text-rose-700")
                }>
                  {money(validation.difference)}
                </p>

              </div>

              <p className="text-xs text-slate-500">
                A aprovação da equação contábil não
                substitui a revisão dos lançamentos
                e das conciliações individuais.
              </p>

            </>

          )}

        </main>

        <footer className="p-5 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">

          <button
            className={secondary}
            disabled={!!busy}
            onClick={() => {

              if (step === 0) {
                close();
              } else {
                setValidation(null);
                setError("");
                setStep(step - 1);
              }

            }}
          >

            {step > 0 && (
              <ArrowLeft className="inline w-4 h-4 mr-1" />
            )}

            {step === 0 ? "Cancelar" : "Voltar"}

          </button>

          {busy ? (

            <div
              role="status"
              className="flex items-center gap-2 text-blue-700 font-semibold text-sm"
            >
              <Loader2 className="w-5 h-5 animate-spin" />
              {busy}
            </div>

          ) : step === 0 ? (

            <button
              className={primary}
              disabled={!file}
              onClick={() => inspect()}
            >
              Analisar planilha
              <ArrowRight className="w-4 h-4" />
            </button>

          ) : step === 1 ? (

            <button
              className={primary}
              disabled={
                !mappingValid ||
                headerRow - 1 !== preview?.header_row
              }
              onClick={validate}
            >
              Validar contabilidade
              <ArrowRight className="w-4 h-4" />
            </button>

          ) : (

            <button
              className={primary}
              disabled={!approved}
              onClick={confirm}
            >
              <ShieldCheck className="w-4 h-4" />
              Confirmar e conciliar
            </button>

          )}

        </footer>

      </div>

    </div>

  );
};
