/**
 * CONCILIA AI - Frontend API Service Client
 */

// Uses relative path if in browser, otherwise fallback to localhost
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

export interface JobData {
  id: string;
  filename: string;
  company_name: string;
  cnpj: string;
  period: string;
  account_code: string;
  initial_balance: string;
  final_reported_balance: string;
  total_credits: string;
  total_debits: string;
  period_net_movement: string;
  status: string;
  math_validation_status: string;
  math_explanation?: any;
  summary: any;
}

export interface Transaction {
  id: string;
  job_id: string;
  row_index: number;
  trans_date: string;
  history: string;
  trans_type: "CREDIT" | "DEBIT";
  amount: string;
  reported_balance?: string;
  extracted_nf?: string;
  extracted_supplier?: string;
  cleaned_supplier?: string;
  category?: string;
  status: string;
  matched_amount: string;
  remaining_amount: string;
  is_reversal: number;
  is_duplicate: number;
}

export interface ReconciliationPair {
  id: string;
  job_id: string;
  match_type: string;
  invoice_trans_id?: string;
  payment_trans_id?: string;
  nf?: string;
  supplier?: string;
  invoice_amount?: string;
  payment_amount?: string;
  reconciled_amount: string;
  difference: string;
  confidence_score: number;
  status: string;
  match_notes?: string;
  created_at: string;
}


// CONCILIA_V5_UPLOAD_SAFE_29C

async function readSafeResponseV5(
  response: Response,
  operation: string
): Promise<any> {
  const raw = await response.text();

  let data: any;

  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(
      `${operation}: resposta invalida do servidor ` +
      `(HTTP ${response.status}).`
    );
  }

  if (!response.ok) {
    let detail = "";

    if (typeof data?.detail === "string") {
      detail = data.detail;
    } else if (Array.isArray(data?.detail)) {
      detail = data.detail
        .map((item: any) => item?.msg || "")
        .filter(Boolean)
        .join("; ");
    }

    throw new Error(
      detail ||
      `${operation} nao concluida (HTTP ${response.status}).`
    );
  }

  if (
    data === null ||
    typeof data !== "object"
  ) {
    throw new Error(
      `${operation}: resposta inesperada do servidor.`
    );
  }

  if (data.success === false) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `${operation} nao concluida.`
    );
  }

  return data;
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  async getJobs() {
    const res = await fetch(`${API_BASE}/jobs`);
    return res.json();
  },

  async getSettings() {
    const res = await fetch(`${API_BASE}/settings`);
    return res.json();
  },

  async updateSettings(settings: any) {
    const res = await fetch(`${API_BASE}/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    return readSafeResponseV5(res, "Salvar configuracoes");
  },

  async reprocessJob(jobId: string) {
    const res = await fetch(`${API_BASE}/reconciliation/${jobId}/reprocess`, {
      method: "POST",
    });
    return readSafeResponseV5(res, "Reprocessamento");
  },



  // CONCILIA_V5_IMPORT_API_29D41

  async previewImportV5(
    file: File,
    headerRow?: number,
    signal?: AbortSignal
  ): Promise<ImportPreviewV5> {

    if (!file || file.size === 0) {
      throw new Error(
        "Selecione uma planilha nao vazia."
      );
    }

    if (file.size > 50 * 1024 * 1024) {
      throw new Error(
        "A planilha ultrapassa o limite de 50 MB."
      );
    }

    const form = new FormData();

    form.append("file", file);

    if (headerRow !== undefined) {
      form.append(
        "header_row",
        String(headerRow)
      );
    }

    const res = await fetch(
      `${API_BASE}/import/preview`,
      {
        method: "POST",
        body: form,
        cache: "no-store",
        signal
      }
    );

    const result = await readSafeResponseV5(
      res,
      "Pre-visualizacao da planilha"
    ) as ImportPreviewV5;

    if (
      !Array.isArray(result.columns) ||
      !Array.isArray(result.sample) ||
      !result.file_hash ||
      !Number.isInteger(result.header_row)
    ) {
      throw new Error(
        "Resposta de pre-visualizacao invalida."
      );
    }

    return result;
  },

  async validateImportV5(
    file: File,
    headerRow: number,
    mapping: ImportMappingV5,
    signal?: AbortSignal
  ): Promise<ImportValidationV5> {

    const required: ImportFieldV5[] = [
      "date",
      "history",
      "debit",
      "credit",
      "balance"
    ];

    if (!file || file.size === 0) {
      throw new Error("Planilha nao selecionada.");
    }

    if (
      !Number.isInteger(headerRow) ||
      headerRow < 0
    ) {
      throw new Error("Cabecalho invalido.");
    }

    if (
      required.some(
        field => !Number.isInteger(mapping[field])
      )
    ) {
      throw new Error(
        "Preencha todas as colunas obrigatorias."
      );
    }

    const indexes = Object.values(mapping);

    if (
      indexes.some(
        index =>
          !Number.isInteger(index) ||
          index < 0
      )
    ) {
      throw new Error("Coluna invalida.");
    }

    if (
      new Set(indexes).size !== indexes.length
    ) {
      throw new Error(
        "Existem colunas repetidas."
      );
    }

    const form = new FormData();

    form.append("file", file);
    form.append(
      "header_row",
      String(headerRow)
    );

    form.append(
      "mapping_json",
      JSON.stringify(mapping)
    );

    const res = await fetch(
      `${API_BASE}/import/validate`,
      {
        method: "POST",
        body: form,
        cache: "no-store",
        signal
      }
    );

    const result = await readSafeResponseV5(
      res,
      "Validacao contabil"
    ) as ImportValidationV5;

    if (
      typeof result.valid !== "boolean" ||
      result.preview_only !== true ||
      !result.mapping_fingerprint ||
      !result.file_hash
    ) {
      throw new Error(
        "Resposta de validacao invalida."
      );
    }

    return result;
  },

  async confirmImportV5(
    file: File,
    validation: ImportValidationV5
  ): Promise<ImportConfirmationV5> {

    if (!file || file.size === 0) {
      throw new Error("Planilha nao selecionada.");
    }

    if (
      !validation.valid ||
      validation.audit_status !== "VALID" ||
      !validation.mapping_fingerprint ||
      validation.transaction_count <= 0 ||
      Number(validation.difference) !== 0
    ) {
      throw new Error(
        "Valide a planilha antes de confirmar."
      );
    }

    const form = new FormData();

    form.append("file", file);

    form.append(
      "header_row",
      String(validation.header_row)
    );

    form.append(
      "column_mapping",
      JSON.stringify(validation.mapping)
    );

    form.append(
      "mapping_fingerprint",
      validation.mapping_fingerprint
    );

    const res = await fetch(
      `${API_BASE}/upload`,
      {
        method: "POST",
        body: form,
        cache: "no-store"
      }
    );

    const result = await readSafeResponseV5(
      res,
      "Confirmacao da importacao"
    ) as ImportConfirmationV5;

    if (
      result.success !== true ||
      typeof result.job_id !== "string" ||
      !result.job_id
    ) {
      throw new Error(
        "Confirmacao de importacao invalida."
      );
    }

    return result;
  },


  async uploadLedger(file: File) {
    if (!file || file.size === 0) {
      throw new Error(
        "Selecione uma planilha contabil nao vazia."
      );
    }

    const formData = new FormData();
    formData.append("file", file);

    let res: Response;

    try {
      res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
        cache: "no-store",
      });
    } catch {
      throw new Error(
        "Nao foi possivel conectar ao Concilia AI. " +
        "Verifique se o programa esta em execucao."
      );
    }

    return readSafeResponseV5(
      res,
      "Importacao do razao"
    );
  },

  async getSummary(jobId: string) {
    const res = await fetch(`${API_BASE}/reconciliation/${jobId}/summary`);
    if (!res.ok) throw new Error("Erro ao carregar resumo");
    return res.json();
  },

  async getTransactions(jobId: string, params?: { trans_type?: string; status?: string; search?: string }) {
    const q = new URLSearchParams();
    if (params?.trans_type) q.append("trans_type", params.trans_type);
    if (params?.status) q.append("status", params.status);
    if (params?.search) q.append("search", params.search);
    const res = await fetch(`${API_BASE}/reconciliation/${jobId}/transactions?${q.toString()}`);
    return res.json();
  },

  async getReconciled(jobId: string, matchType?: string) {
    const url = matchType 
      ? `${API_BASE}/reconciliation/${jobId}/reconciled?match_type=${matchType}`
      : `${API_BASE}/reconciliation/${jobId}/reconciled`;
    const res = await fetch(url);
    return res.json();
  },

  async getOpen(jobId: string) {
    const res = await fetch(`${API_BASE}/reconciliation/${jobId}/open`);
    return res.json();
  },

  async getDivergences(jobId: string) {
    const res = await fetch(`${API_BASE}/reconciliation/${jobId}/divergences`);
    return res.json();
  },

  async getSupplierSummary(jobId: string) {
    const res = await fetch(`${API_BASE}/reconciliation/${jobId}/supplier-summary`);
    return res.json();
  },

  // CONCILIA_V5_APPROVAL_UI_30A3C2
  async manualMatch(
    jobId: string,
    invoiceTransId: string,
    paymentTransId: string,
    notes?: string,
    approval?: {
      expected_invoice_remaining: string;
      expected_payment_remaining: string;
      approval_source: "MANUAL" | "SUGGESTION" | "BATCH";
      confirm_review?: boolean;
    }
  ) {
    const res = await fetch(`${API_BASE}/reconciliation/${jobId}/manual-match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        invoice_trans_id: invoiceTransId,
        payment_trans_id: paymentTransId,
        ...(approval || {}),
        notes: notes || "Conciliação manual aprovada.",
      }),
    });

    // CONCILIA_V5_HTTP_ERRORS
    const raw = await res.text();
    let data: any;

    try {
      data = JSON.parse(raw);
    } catch {
      throw new Error(
        "Resposta invalida do servidor. HTTP " + res.status
      );
    }

    if (!res.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Falha na conciliacao. HTTP " + res.status
      );
    }

    return data;
  },

  getTabExportUrl(jobId: string, tab: string) {
    return `${API_BASE}/reconciliation/${encodeURIComponent(jobId)}/export/tab/${encodeURIComponent(tab)}`;
  },

  getExcelExportUrl(jobId: string) {
    return `${API_BASE}/reconciliation/${jobId}/export/excel`;
  },

  getPdfExportUrl(jobId: string) {
    return `${API_BASE}/reconciliation/${jobId}/export/pdf`;
  }
};


export async function deleteHistory(jobId?: string) {
  const url = jobId
    ? `${API_BASE}/history/${encodeURIComponent(jobId)}`
    : `${API_BASE}/history`;
  const response = await fetch(url, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Nao foi possivel excluir o documento.");
  }
  return response.json();
}

export async function attachOpening(
  id: string,
  file: File
) {
  if (!file || file.size === 0) {
    throw new Error(
      "Selecione uma planilha de saldo anterior valida."
    );
  }

  const body = new FormData();
  body.append("file", file);

  const res = await fetch(
    `${API_BASE}/reconciliation/${encodeURIComponent(id)}/opening`,
    {
      method: "POST",
      body,
      cache: "no-store"
    }
  );

  return readSafeResponseV5(
    res,
    "Importacao do saldo anterior"
  );
}


export async function getSmartSuggestions(jobId: string) {
    const res = await fetch(
        `${API_BASE}/reconciliation/${encodeURIComponent(jobId)}/suggestions`,
        { cache: "no-store" }
    );

    const data = await res.json();

    if (!res.ok) {
        throw new Error(data.detail || "Erro ao carregar sugestoes.");
    }

    return data;
}



 // CONCILIA_V5_OPENING_CLIENT

export interface OpeningSuggestionV5 {
  opening_index: number;
  payment_trans_id: string;
  opening_nf?: string;
  payment_nf?: string;
  opening_hash: string;
  opening_amount: string;
  payment_amount: string;
  opening_after: string;
  payment_after: string;
  category: string;
  reason: string;
  automatic_eligible: boolean;
  ambiguous: boolean;
  current_conflict?: boolean;
}

export interface OpeningDataV5 {
  opening_attached: boolean;
  items: OpeningSuggestionV5[];
  total: number;
  eligible: number;
  ambiguous: number;
  partial: number;
  approved_count: number;
  approved_amount: string;
  opening_rows: any[];
}

async function openingRequestV5(
  url: string,
  options?: RequestInit
) {
  const res = await fetch(url, {
    ...options,
    cache: "no-store"
  });

  const raw = await res.text();
  let data: any;

  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(
      `Resposta invalida do servidor (HTTP ${res.status}).`
    );
  }

  if (!res.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Operacao bloqueada (HTTP ${res.status}).`
    );
  }

  return data;
}

export async function getOpeningSuggestionsV5(
  jobId: string
): Promise<OpeningDataV5> {
  return openingRequestV5(
    `${API_BASE}/reconciliation/${encodeURIComponent(jobId)}/opening-suggestions`
  );
}

export async function approveOpeningV5(
  jobId: string,
  item: OpeningSuggestionV5
) {
  return openingRequestV5(
    `${API_BASE}/reconciliation/${encodeURIComponent(jobId)}/opening-approve`,
    {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        opening_index: item.opening_index,
        payment_trans_id: item.payment_trans_id,
        opening_hash: item.opening_hash,
        expected_opening: item.opening_amount,
        expected_payment: item.payment_amount,
        confirm_review: true
      })
    }
  );
}


// CONCILIA_V5_UNDO_CLIENT

export async function undoReconciliationV5(
  jobId: string,
  matchId: string,
  origin: "CURRENT" | "OPENING",
  reason: string
) {
  const res = await fetch(
    `${API_BASE}/reconciliation/${encodeURIComponent(jobId)}/undo-match`,
    {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      cache: "no-store",
      body: JSON.stringify({
        match_id: matchId,
        origin,
        reason,
        confirm: true
      })
    }
  );

  const raw = await res.text();

  let data: any;

  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(
      `Resposta invalida do servidor (HTTP ${res.status}). Atualize os dados antes de tentar novamente.`
    );
  }

  if (!res.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Operacao bloqueada (HTTP ${res.status}).`
    );
  }

  return data;
}

export async function getUndoHistoryV5(jobId: string) {

  const res = await fetch(
    `${API_BASE}/reconciliation/${encodeURIComponent(jobId)}/undo-history`,
    {cache: "no-store"}
  );

  if (!res.ok) {
    throw new Error(
      `Falha ao consultar historico (HTTP ${res.status}).`
    );
  }

  return res.json();
}


// CONCILIA_V5_IMPORT_TYPES_29D41

export type ImportFieldV5 =
  | "date"
  | "history"
  | "debit"
  | "credit"
  | "balance"
  | "document";

export type ImportMappingV5 =
  Partial<Record<ImportFieldV5, number>>;

export interface ImportColumnV5 {
  index: number;
  letter: string;
  header: string;
}

export interface ImportPreviewV5 {
  filename: string;
  file_hash: string;
  row_count: number;
  column_count: number;
  header_row: number;
  columns: ImportColumnV5[];
  sample: {
    row: number;
    values: string[];
  }[];
  automatic_mapping: {
    header_row: number;
    mapping: ImportMappingV5;
  } | null;
  requires_manual_mapping: boolean;
  warning: string | null;
}

export interface ImportValidationV5 {
  valid: boolean;
  transaction_count: number;
  initial_balance: string;
  total_debits: string;
  total_credits: string;
  calculated_balance: string;
  reported_balance: string;
  difference: string;
  audit_status: string;
  file_hash: string;
  mapping_fingerprint: string;
  header_row: number;
  mapping: ImportMappingV5;
  sample: unknown[];
  preview_only: boolean;
}

export interface ImportConfirmationV5 {
  success: boolean;
  job_id: string;
  message: string;
  summary: unknown;
  math_audit: unknown;
}

