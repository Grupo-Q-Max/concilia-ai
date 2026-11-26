"use client";

// CONCILIA_V5_EXPORT_BUTTON_24D
import ExportSuggestionsButton from "@/components/ExportSuggestionsButton";

import React, { useEffect, useRef, useState } from "react";
import {
    Sparkles, CheckCircle2, AlertTriangle,
    RefreshCw, Search, ArrowRight, Loader2,
    ChevronDown, ChevronUp, ChevronsUpDown, CheckCheck, X
} from "lucide-react";
import { api, getSmartSuggestions } from "@/lib/api";

interface Suggestion {
    id: string;
    invoice_trans_id: string;
    payment_trans_id: string;
    invoice_nf: string;
    payment_nf: string;
    invoice_supplier?: string;
    payment_supplier?: string;
    invoice_date?: string;
    payment_date?: string;
    invoice_history?: string;
    payment_history?: string;
    invoice_remaining: string;
    payment_remaining: string;
    suggested_amount: string;
    invoice_after: string;
    payment_after: string;
    score: number;
    reason: string;
    category: string;
    ambiguous: boolean;
    batch_eligible: boolean;
    fiscal_equivalent?: boolean;
    requires_individual_review?: boolean;
}

interface ApprovalProgress {
    total: number;
    current: number;
    currentNf: string;
    currentSupplier?: string;
    currentAmount?: string;
    mode: "SUGGESTION" | "BATCH" | "SELECTED";
}

interface Props {
    revision: number;
    jobId: string;
    onRefresh: () => Promise<void>;
}

const money = (value: string | number) =>
    Number(value || 0).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    });

const formatDate = (val?: string) => {
    if (!val) return "-";
    const parts = val.split("-");
    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return val;
};

const labels: Record<string, string> = {
    COMPATIVEL: "Compativel",
    DIVERGENCIA_NF: "Revisar NF",
    PARCIAL: "Baixa parcial",
    BAIXA_EVIDENCIA: "Evidencia insuficiente"
};

export const displayNf = (nf?: string, history?: string): string => {
    const raw = String(nf || "").trim();
    const cleanRaw = raw.toUpperCase().replace(/^NF[-:\s]*/i, "").trim();
    if (cleanRaw && !["S/N", "SN", "0", "-", "NONE", "NAN", "N/A", "SEM NOTA", ""].includes(cleanRaw)) {
        return cleanRaw;
    }
    if (history) {
        const cleaned = history
            .replace(/\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b/g, " ")
            .replace(/\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b/g, " ")
            .replace(/\b\d{1,2}\/\d{4}\b/g, " ")
            .replace(/\b\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}\b/g, " ")
            .replace(/\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g, " ")
            .replace(/\b\d{11,14}\b/g, " ")
            .replace(/R\$\s*[\d\.,]+/gi, " ")
            .replace(/\b\d{1,3}(?:\.\d{3})*,\d{2}\b/g, " ")
            .replace(/\b\d+,\d{2}\b/g, " ")
            .replace(/\b\d{1,2}:\d{2}(?::\d{2})?\b/g, " ")
            .replace(/\/\s*\d+\b/g, " ");

        const mPref = cleaned.match(/\b(?:CRF|NF-?E?|N\.?F\.?|NOTA\s+FISCAL|DOC(?:UMENTO)?|TIT(?:ULO)?|DUPLICATA|FATURA|REC(?:IBO)?|PED(?:IDO)?|GUIA)\b.*?\b(\d{1,10})\b/i);
        if (mPref) {
            return String(parseInt(mPref[1], 10));
        }
        const mCorp = cleaned.match(/\b(?:LTDA|EIRELI|EPP|ME|S\/?A|SA|SOCIEDADE\s+ANONIMA|UNIPESSOAL)\b.*?\b(\d{1,10})\s*$/i);
        if (mCorp) {
            return String(parseInt(mCorp[1], 10));
        }
        const mEnd = cleaned.match(/\b(\d{1,10})\s*$/);
        if (mEnd) {
            return String(parseInt(mEnd[1], 10));
        }
        const nums = cleaned.match(/\b(\d{1,10})\b/g);
        if (nums && nums.length > 0) {
            return String(parseInt(nums[nums.length - 1], 10));
        }
    }
    return cleanRaw && cleanRaw !== "0" ? cleanRaw : "S/N";
};

export default function SmartSuggestions({
    jobId, onRefresh, revision
}: Props) {

    const [items, setItems] = useState<Suggestion[]>([]);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [progress, setProgress] = useState<ApprovalProgress | null>(null);
    const [approvingId, setApprovingId] = useState<string | null>(null);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");
    const [filter, setFilter] = useState("TODOS");
    const [search, setSearch] = useState("");
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
    const lock = useRef(false);

    // CONCILIA_V5_SAFE_SUGGESTIONS_23E
    const requestV5 = useRef(0);

    async function load() {
        const seq = ++requestV5.current;
        setLoading(true);

        try {
            const data = await getSmartSuggestions(jobId);
            if (seq !== requestV5.current) return;

            if (!Array.isArray(data.items)) {
                throw new Error("Resposta de sugestoes invalida.");
            }

            setItems(data.items);
            // Retain selected items that still exist
            setSelectedIds(prev => {
                const available = new Set(data.items.map((i: Suggestion) => i.id));
                const filtered = new Set<string>();
                prev.forEach(id => {
                    if (available.has(id)) filtered.add(id);
                });
                return filtered;
            });
        } catch (e) {
            if (seq !== requestV5.current) return;
            setItems([]);
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            if (seq === requestV5.current) {
                setLoading(false);
            }
        }
    }

    useEffect(() => {
        void load();
        return () => {
            requestV5.current++;
        };
    }, [jobId, revision]);

    // CONCILIA_V5_APPROVAL_UI_30A3C2
    async function approve(
        list: Suggestion[],
        mode: "SUGGESTION" | "BATCH" | "SELECTED" = "SUGGESTION"
    ) {
        if (lock.current || !list.length || loading) return;

        if (mode === "SUGGESTION" && list.length !== 1) {
            setError("Selecione uma sugestao por vez.");
            return;
        }

        if (mode === "BATCH" && list.some(s =>
            !s.batch_eligible ||
            s.ambiguous ||
            s.fiscal_equivalent ||
            s.requires_individual_review ||
            s.category !== "COMPATIVEL"
        )) {
            setError("O lote contem sugestoes que exigem revisao individual.");
            return;
        }

        const reviewCount = list.filter(s =>
            s.ambiguous ||
            s.fiscal_equivalent ||
            s.requires_individual_review ||
            s.category !== "COMPATIVEL"
        ).length;

        const requiresReview = reviewCount > 0;

        let confirmMsg = "";
        if (mode === "SUGGESTION") {
            confirmMsg = requiresReview
                ? "Esta sugestao possui candidatos alternativos ou observacoes. Deseja aprovar a baixa?"
                : "Confirmar aprovacao desta conciliacao?";
        } else if (mode === "SELECTED") {
            confirmMsg = requiresReview
                ? `Confirmar aprovacao simultanea de ${list.length} conciliacao(oes) selecionada(s)? (${reviewCount} possuem observacoes/candidatos alternativos e serao confirmadas).`
                : `Confirmar aprovacao simultanea de ${list.length} conciliacao(oes) selecionada(s)?`;
        } else {
            confirmMsg = `Confirmar ${list.length} conciliacao(oes) compativeis em lote?`;
        }

        if (!window.confirm(confirmMsg)) return;

        lock.current = true;
        setBusy(true);
        setError("");
        setMessage("");

        setProgress({
            total: list.length,
            current: 0,
            currentNf: "",
            mode
        });

        let completed = 0;
        const failed: string[] = [];

        try {
            for (let i = 0; i < list.length; i++) {
                const item = list[i];
                const currentNf = displayNf(item.invoice_nf, item.invoice_history);
                setApprovingId(item.id);

                setProgress({
                    total: list.length,
                    current: i + 1,
                    currentNf,
                    currentSupplier: item.invoice_supplier || item.payment_supplier,
                    currentAmount: item.suggested_amount,
                    mode
                });

                try {
                    const latest = await getSmartSuggestions(jobId);

                    const current = (latest.items || []).find(
                        (s: Suggestion) => s.id === item.id
                    );

                    if (!current) {
                        failed.push(`NF ${currentNf}: lancamento ja liquidado ou modificado.`);
                        continue;
                    }

                    if (
                        current.invoice_remaining !== item.invoice_remaining ||
                        current.payment_remaining !== item.payment_remaining ||
                        current.suggested_amount !== item.suggested_amount
                    ) {
                        failed.push(`NF ${currentNf}: saldo modificado por outra baixa.`);
                        continue;
                    }

                    const requiresIndividual = Boolean(
                        current.ambiguous ||
                        current.fiscal_equivalent ||
                        current.requires_individual_review ||
                        current.category !== "COMPATIVEL" ||
                        !current.batch_eligible
                    );

                    const approvalSource = (mode === "BATCH" || (!requiresIndividual && mode === "SELECTED"))
                        ? "BATCH"
                        : "SUGGESTION";

                    const result = await api.manualMatch(
                        jobId,
                        item.invoice_trans_id,
                        item.payment_trans_id,
                        "Sugestao inteligente aprovada: " + item.reason,
                        {
                            expected_invoice_remaining: String(current.invoice_remaining),
                            expected_payment_remaining: String(current.payment_remaining),
                            approval_source: approvalSource,
                            confirm_review: true
                        }
                    );

                    if (!result.success) {
                        failed.push(`NF ${currentNf}: ${result.detail || "Falha ao registrar baixa."}`);
                        continue;
                    }

                    completed++;

                    setSelectedIds(prev => {
                        const next = new Set(prev);
                        next.delete(item.id);
                        return next;
                    });
                } catch (itemErr) {
                    failed.push(`NF ${currentNf}: ${itemErr instanceof Error ? itemErr.message : String(itemErr)}`);
                }
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setProgress(null);
            setApprovingId(null);

            if (completed > 0) {
                try {
                    await onRefresh();
                } catch (e) {
                    setError(previous =>
                        previous + " Baixas registradas, mas os indicadores precisam ser atualizados."
                    );
                }
            }

            await load();

            if (failed.length > 0 && completed > 0) {
                setMessage(`${completed} conciliacao(oes) registrada(s) com sucesso. ${failed.length} nao concluida(s): ${failed.join("; ")}`);
            } else if (failed.length > 0 && completed === 0) {
                setError(`Nenhuma baixa registrada: ${failed.join("; ")}`);
            } else {
                setMessage(`${completed} conciliacao(oes) registrada(s) com sucesso de ${list.length}.`);
            }

            lock.current = false;
            setBusy(false);
        }
    }

    const eligible = items.filter(s =>
        s.batch_eligible &&
        !s.ambiguous &&
        !s.fiscal_equivalent &&
        !s.requires_individual_review &&
        s.category === "COMPATIVEL"
    );

    const visible = items.filter(s => {
        const q = search.toLowerCase();
        const invNf = displayNf(s.invoice_nf, s.invoice_history);
        const payNf = displayNf(s.payment_nf, s.payment_history);

        return (
            (filter === "TODOS" || s.category === filter) &&
            [
                s.invoice_nf, s.payment_nf,
                invNf, payNf,
                s.invoice_supplier, s.payment_supplier,
                s.invoice_history, s.payment_history
            ].join(" ").toLowerCase().includes(q)
        );
    });

    const selectedItems = visible.filter(s => selectedIds.has(s.id));
    const totalSelectedAmount = selectedItems.reduce(
        (acc, s) => acc + Number(s.suggested_amount || 0),
        0
    );

    const toggleSelect = (id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const toggleSelectAllVisible = () => {
        const visibleIds = visible.filter(s => s.category !== "BAIXA_EVIDENCIA").map(s => s.id);
        const allSelected = visibleIds.length > 0 && visibleIds.every(id => selectedIds.has(id));
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (allSelected) {
                visibleIds.forEach(id => next.delete(id));
            } else {
                visibleIds.forEach(id => next.add(id));
            }
            return next;
        });
    };

    const toggleExpand = (id: string) => {
        setExpandedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const toggleExpandAll = () => {
        const visibleIds = visible.map(s => s.id);
        const allExpanded = visibleIds.length > 0 && visibleIds.every(id => expandedIds.has(id));
        if (allExpanded) {
            setExpandedIds(new Set());
        } else {
            setExpandedIds(new Set(visibleIds));
        }
    };

    const allVisibleSelected = visible.length > 0 &&
        visible.filter(s => s.category !== "BAIXA_EVIDENCIA").length > 0 &&
        visible.filter(s => s.category !== "BAIXA_EVIDENCIA").every(s => selectedIds.has(s.id));

    const allVisibleExpanded = visible.length > 0 && visible.every(s => expandedIds.has(s.id));

    return (
        <section className="space-y-4">

            {/* EXPORT PANEL */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
                <div>
                    <p className="text-sm font-bold text-slate-800">
                        Exportacao das sugestoes inteligentes
                    </p>
                    <p className="text-xs text-slate-500">
                        Relatorio completo em Excel, sem aprovar baixas.
                    </p>
                </div>

                <ExportSuggestionsButton
                    key={jobId}
                    jobId={jobId}
                    tab="suggestions"
                    label="Exportar sugestoes em Excel"
                    disabled={busy || loading}
                />
            </div>

            {/* HEADER BANNER */}
            <div className="rounded-2xl bg-slate-900 p-5 sm:p-6 text-white shadow-lg">
                <div className="flex items-center gap-3">
                    <Sparkles className="h-7 w-7 text-sky-400 shrink-0"/>
                    <div>
                        <h2 className="text-xl font-bold">
                            Conciliacao Inteligente
                        </h2>
                        <p className="text-xs sm:text-sm text-slate-300">
                            Analise, revise e aprove sugestoes individuais ou simultaneamente em lote.
                        </p>
                    </div>
                </div>
            </div>

            {/* METRICS SUMMARY */}
            <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                {[
                    ["Sugestoes", items.length],
                    ["Compativeis", items.filter(s => s.category === "COMPATIVEL").length],
                    ["Revisar NF", items.filter(s => s.category === "DIVERGENCIA_NF").length],
                    ["Baixas parciais", items.filter(s => s.category === "PARCIAL").length]
                ].map(([label, value]) => (
                    <div key={label}
                        className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs">
                        <p className="text-xs font-semibold text-slate-500">
                            {label}
                        </p>
                        {loading ? (
                            <div className="mt-2 h-7 w-14 bg-slate-200 rounded animate-pulse" />
                        ) : (
                            <p className="mt-1 text-2xl font-bold text-slate-900">
                                {value}
                            </p>
                        )}
                    </div>
                ))}
            </div>

            {/* FILTER & ACTIONS TOOLBAR */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[280px]">
                    <div className="flex items-center gap-2 rounded-lg border bg-slate-50 px-3 py-1.5 flex-1 max-w-xs">
                        <Search className="h-4 w-4 text-slate-400"/>
                        <input
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar NF ou fornecedor"
                            className="w-full bg-transparent text-sm outline-none placeholder:text-slate-400"
                        />
                    </div>

                    <select
                        value={filter}
                        onChange={e => setFilter(e.target.value)}
                        className="rounded-lg border bg-slate-50 px-3 py-1.5 text-sm outline-none"
                    >
                        <option value="TODOS">Todas as sugestoes</option>
                        {Object.entries(labels).map(([key, label]) => (
                            <option key={key} value={key}>{label}</option>
                        ))}
                    </select>

                    <button
                        disabled={busy || loading}
                        onClick={() => void load()}
                        className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60 transition-colors"
                        title="Atualizar sugestoes"
                    >
                        <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-blue-600" : ""}`}/>
                        <span>{loading ? "Carregando..." : "Atualizar"}</span>
                    </button>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {/* EXPAND ALL / COLLAPSE ALL TOGGLE */}
                    <button
                        type="button"
                        onClick={toggleExpandAll}
                        disabled={!visible.length || loading}
                        className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        title={allVisibleExpanded ? "Recolher todos os cards" : "Expandir todos os cards"}
                    >
                        <ChevronsUpDown className="h-3.5 w-3.5 text-slate-500" />
                        {allVisibleExpanded ? "Recolher todos" : "Expandir todos"}
                    </button>

                    {/* APPROVE ALL ELIGIBLE QUICK BUTTON */}
                    <button
                        disabled={busy || loading || !eligible.length}
                        onClick={() => void approve(eligible, "BATCH")}
                        className="rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-emerald-700 disabled:opacity-40 transition-colors"
                        title="Aprova todas as sugestões 100% compatíveis sem ambiguidades"
                    >
                        Aprovar compativeis ({eligible.length})
                    </button>
                </div>
            </div>

            {/* SELECTION BAR (Aparece quando há itens selecionados para aprovação simultânea) */}
            {selectedItems.length > 0 && !progress && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border-2 border-blue-500 bg-blue-50 p-3.5 shadow-md animate-in fade-in duration-200">
                    <div className="flex items-center gap-3">
                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                            {selectedItems.length}
                        </span>
                        <div>
                            <p className="text-sm font-bold text-blue-950">
                                {selectedItems.length} {selectedItems.length === 1 ? "conciliacao selecionada" : "conciliacoes selecionadas"}
                            </p>
                            <p className="text-xs text-blue-700">
                                Total: <strong className="font-semibold text-blue-900">{money(totalSelectedAmount)}</strong>
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            disabled={busy || loading}
                            onClick={() => setSelectedIds(new Set())}
                            className="flex items-center gap-1 rounded-lg border border-blue-300 bg-white px-3 py-1.5 text-xs font-semibold text-blue-800 hover:bg-blue-100 disabled:opacity-50"
                        >
                            <X className="h-3.5 w-3.5" />
                            Desmarcar
                        </button>

                        <button
                            type="button"
                            disabled={busy || loading}
                            onClick={() => void approve(selectedItems, "SELECTED")}
                            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
                        >
                            <CheckCheck className="h-4 w-4" />
                            Aprovar selecionados ({selectedItems.length})
                        </button>
                    </div>
                </div>
            )}

            {/* STATUS DE PROGRESSO EM LOTE / APROVAÇÃO SIMULTÂNEA */}
            {progress && (
                <div className="rounded-xl border-2 border-blue-500 bg-blue-50 p-4 shadow-md space-y-3 animate-in fade-in duration-200">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                            <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-white shadow-xs">
                                <Loader2 className="h-5 w-5 animate-spin" />
                            </div>
                            <div>
                                <h4 className="text-sm font-bold text-blue-950">
                                    {progress.total === 1
                                        ? "Aprovando conciliação inteligente..."
                                        : `Aprovando conciliações simultâneas (${progress.current} de ${progress.total})`}
                                </h4>
                                <p className="text-xs text-blue-700 mt-0.5">
                                    {progress.currentNf ? `NF ${progress.currentNf}` : ""}
                                    {progress.currentSupplier ? ` • ${progress.currentSupplier}` : ""}
                                    {progress.currentAmount ? ` • ${money(progress.currentAmount)}` : ""}
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold text-blue-900 bg-white border border-blue-200 px-2.5 py-1 rounded-md shadow-2xs">
                                {Math.round((progress.current / Math.max(progress.total, 1)) * 100)}%
                            </span>
                        </div>
                    </div>

                    {/* Barra de Progresso Animada */}
                    <div className="w-full bg-blue-200 rounded-full h-2.5 overflow-hidden">
                        <div
                            className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out"
                            style={{ width: `${Math.round((progress.current / Math.max(progress.total, 1)) * 100)}%` }}
                        />
                    </div>

                    <p className="text-[11px] text-blue-700 italic">
                        Validando regras fiscais, saldos residuais e gravando auditoria no razão contábil...
                    </p>
                </div>
            )}

            {/* FEEDBACK MESSAGES */}
            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                    {error}
                </div>
            )}

            {message && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 flex flex-wrap items-center justify-between gap-3">
                    <p className="font-medium">{message}</p>
                    <button
                        disabled={busy}
                        onClick={() => {
                            void onRefresh().catch(e =>
                                setError(e instanceof Error ? e.message : String(e))
                            );
                        }}
                        className="rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-blue-700"
                    >
                        Atualizar todas as abas
                    </button>
                </div>
            )}

            {/* LIST HEADER: SELECT ALL / ITEM COUNT */}
            {!loading && visible.length > 0 && (
                <div className="flex items-center justify-between px-1 text-xs text-slate-500">
                    <label className="flex items-center gap-2 cursor-pointer select-none font-medium hover:text-slate-800">
                        <input
                            type="checkbox"
                            checked={allVisibleSelected}
                            onChange={toggleSelectAllVisible}
                            disabled={busy || loading}
                            className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                        <span>Selecionar todos ({visible.length})</span>
                    </label>

                    <span>
                        Exibindo {visible.length} {visible.length === 1 ? "sugestao" : "sugestoes"}
                    </span>
                </div>
            )}

            {/* LOADING STATE ENHANCED COM STATUS E SKELETON */}
            {loading && (
                <div className="space-y-3">
                    {/* Banner Informativo de Carregamento */}
                    <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-4 shadow-xs flex items-center justify-between gap-3 animate-pulse">
                        <div className="flex items-center gap-3">
                            <Loader2 className="h-5 w-5 animate-spin text-blue-600 shrink-0" />
                            <div>
                                <p className="text-sm font-bold text-blue-950">
                                    Carregando conciliação inteligente...
                                </p>
                                <p className="text-xs text-blue-700 mt-0.5">
                                    Cruzando provisões e pagamentos em aberto para gerar sugestões automáticas.
                                </p>
                            </div>
                        </div>
                        <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-white text-blue-800 border border-blue-200 shadow-2xs">
                            <span className="h-2 w-2 rounded-full bg-blue-600 animate-ping" />
                            Analisando lançamentos
                        </span>
                    </div>

                    {/* Skeletons dos cards */}
                    <div className="space-y-2.5">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs animate-pulse">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="flex items-center gap-3 flex-1">
                                        <div className="h-4 w-4 bg-slate-200 rounded shrink-0" />
                                        <div className="h-5 w-24 bg-slate-200 rounded-full" />
                                        <div className="h-5 w-16 bg-slate-200 rounded-md" />
                                        <div className="h-4 w-48 bg-slate-200 rounded hidden md:block" />
                                    </div>
                                    <div className="flex items-center gap-2.5 shrink-0">
                                        <div className="h-5 w-20 bg-slate-200 rounded" />
                                        <div className="h-7 w-16 bg-slate-200 rounded-lg" />
                                        <div className="h-7 w-20 bg-slate-200 rounded-lg" />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* EMPTY STATE */}
            {!loading && !visible.length && !error && (
                <div className="rounded-2xl border bg-white p-10 text-center text-slate-500">
                    Nenhuma sugestao encontrada para este filtro.
                </div>
            )}

            {/* SUGGESTION CARDS LIST (COMPACT WITH EXPAND OPTION) */}
            {!loading && visible.map(s => {
                const isSelected = selectedIds.has(s.id);
                const isExpanded = expandedIds.has(s.id);
                const isThisApproving = approvingId === s.id;
                const nfDisplay = displayNf(s.invoice_nf, s.invoice_history);
                const supplierName = s.invoice_supplier || s.payment_supplier || s.invoice_history || "Sem fornecedor identificado";

                return (
                    <article
                        key={s.id}
                        className={`rounded-xl border transition-all ${
                            isThisApproving
                                ? "border-blue-500 bg-blue-50/40 shadow-sm ring-1 ring-blue-400"
                                : isSelected
                                ? "border-blue-400 bg-blue-50/20 shadow-sm ring-1 ring-blue-300"
                                : "border-slate-200 bg-white hover:border-slate-300 shadow-xs"
                        }`}
                    >
                        {/* COMPACT CARD ROW */}
                        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 sm:p-4">
                            {/* Left Side: Checkbox + Status Badge + NF Badge + Supplier & Dates */}
                            <div className="flex min-w-0 flex-1 items-center gap-3">
                                <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleSelect(s.id)}
                                    disabled={busy || loading || s.category === "BAIXA_EVIDENCIA"}
                                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer shrink-0"
                                    title="Selecionar para aprovacao simultanea"
                                />

                                <div className="flex flex-wrap items-center gap-2">
                                    {/* Category Pill */}
                                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                        s.category === "COMPATIVEL"
                                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                            : s.category === "PARCIAL"
                                            ? "bg-blue-50 text-blue-700 border border-blue-200"
                                            : "bg-amber-50 text-amber-700 border border-amber-200"
                                    }`}>
                                        {s.category === "COMPATIVEL" ? (
                                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                                        ) : (
                                            <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                                        )}
                                        {labels[s.category] || s.category}
                                    </span>

                                    {/* NF Tag */}
                                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-800">
                                        NF {nfDisplay}
                                    </span>

                                    {/* Ambiguous indicator badge */}
                                    {s.ambiguous && (
                                        <span className="hidden sm:inline-flex rounded-md bg-amber-50 border border-amber-200 px-2 py-0.5 text-[11px] font-medium text-amber-800" title="Existem outros candidatos no extrato">
                                            Outros candidatos
                                        </span>
                                    )}
                                </div>

                                {/* Supplier & Dates summary (Desktop) */}
                                <div className="min-w-0 flex-1 hidden md:block">
                                    <p className="truncate text-xs font-medium text-slate-700" title={supplierName}>
                                        {supplierName}
                                    </p>
                                    <p className="text-[11px] text-slate-400">
                                        {formatDate(s.invoice_date)} ➔ {formatDate(s.payment_date)}
                                    </p>
                                </div>
                            </div>

                            {/* Right Side: Suggested Amount + Details button + Quick Approve button */}
                            <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
                                <span className="text-sm sm:text-base font-bold text-emerald-700">
                                    {money(s.suggested_amount)}
                                </span>

                                <button
                                    type="button"
                                    onClick={() => toggleExpand(s.id)}
                                    className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
                                    title={isExpanded ? "Recolher detalhes" : "Expandir detalhes"}
                                >
                                    <span>{isExpanded ? "Recolher" : "Detalhes"}</span>
                                    {isExpanded ? (
                                        <ChevronUp className="h-3.5 w-3.5 text-slate-500" />
                                    ) : (
                                        <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
                                    )}
                                </button>

                                <button
                                    disabled={busy || loading || s.category === "BAIXA_EVIDENCIA"}
                                    onClick={() => void approve([s], "SUGGESTION")}
                                    className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-40 transition-colors min-w-[76px] justify-center"
                                    title="Aprovar esta conciliacao"
                                >
                                    {isThisApproving ? (
                                        <>
                                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                            <span>Aprovando...</span>
                                        </>
                                    ) : (
                                        <>
                                            <span>Aprovar</span>
                                            <ArrowRight className="h-3.5 w-3.5" />
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Supplier & Dates summary (Mobile) */}
                        <div className="px-3.5 pb-2.5 md:hidden text-xs text-slate-600 flex justify-between items-center border-t border-slate-100 pt-1.5">
                            <span className="truncate max-w-[200px]" title={supplierName}>
                                {supplierName}
                            </span>
                            <span className="text-[11px] text-slate-400">
                                {formatDate(s.invoice_date)} ➔ {formatDate(s.payment_date)}
                            </span>
                        </div>

                        {/* EXPANDED CONTENT (Quando expandido) */}
                        {isExpanded && (
                            <div className="border-t border-slate-200 bg-slate-50/60 p-4 space-y-3.5 animate-in fade-in-50 duration-150">
                                <p className="text-xs font-medium text-slate-600">{s.reason}</p>

                                <div className="grid gap-3 md:grid-cols-2">
                                    {[
                                        {
                                            label: "Provisao / Credito",
                                            nf: displayNf(s.invoice_nf, s.invoice_history),
                                            supplier: s.invoice_supplier,
                                            date: s.invoice_date,
                                            history: s.invoice_history,
                                            value: s.invoice_remaining
                                        },
                                        {
                                            label: "Pagamento / Debito",
                                            nf: displayNf(s.payment_nf, s.payment_history),
                                            supplier: s.payment_supplier,
                                            date: s.payment_date,
                                            history: s.payment_history,
                                            value: s.payment_remaining
                                        }
                                    ].map(t => (
                                        <div key={t.label} className="space-y-1.5 rounded-xl bg-white border border-slate-200/80 p-3.5 shadow-xs">
                                            <div className="flex items-center justify-between">
                                                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                                                    {t.label}
                                                </span>
                                                <span className="text-xs font-bold text-slate-900">
                                                    NF {t.nf}
                                                </span>
                                            </div>
                                            <p className="text-sm font-semibold text-slate-800">
                                                {t.supplier || "Fornecedor nao identificado"}
                                            </p>
                                            <p className="text-xs text-slate-500">
                                                {t.date ? formatDate(t.date) : "Sem data"}
                                            </p>
                                            <p className="break-words text-xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-100">
                                                {t.history || "Sem historico"}
                                            </p>
                                            <p className="text-xs font-bold text-slate-900">
                                                Saldo: {money(t.value)}
                                            </p>
                                        </div>
                                    ))}
                                </div>

                                <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-200 bg-white p-3 text-xs">
                                    <div>
                                        <p className="text-slate-500">Saldo da NF apos baixa</p>
                                        <strong className="text-slate-800">{money(s.invoice_after)}</strong>
                                    </div>
                                    <div>
                                        <p className="text-slate-500">Saldo do pagamento</p>
                                        <strong className="text-slate-800">{money(s.payment_after)}</strong>
                                    </div>
                                </div>

                                {s.ambiguous && (
                                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs font-medium text-amber-800 flex items-center gap-2">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        <span>Existem outros candidatos. Confira os historicos antes de aprovar.</span>
                                    </div>
                                )}
                            </div>
                        )}
                    </article>
                );
            })}

        </section>
    );
}
