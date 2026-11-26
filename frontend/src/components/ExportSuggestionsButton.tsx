
"use client";

// CONCILIA_V5_EXPORT_BUTTON_24D

import React, {
    useEffect,
    useRef,
    useState
} from "react";

import {
    FileSpreadsheet,
    Loader2
} from "lucide-react";

import { api } from "@/lib/api";

type Props = {
    jobId: string;
    tab: "suggestions" | "opening-suggestions";
    label: string;
    disabled?: boolean;
};

export default function ExportSuggestionsButton({
    jobId,
    tab,
    label,
    disabled = false
}: Props) {

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    const lock = useRef(false);
    const request = useRef<AbortController | null>(null);

    useEffect(() => {

        setLoading(false);
        setError("");
        setMessage("");
        lock.current = false;

        return () => {
            request.current?.abort();
            request.current = null;
        };

    }, [jobId, tab]);

    async function download() {

        if (disabled || lock.current || !jobId) {
            return;
        }

        lock.current = true;

        const controller = new AbortController();

        request.current = controller;

        setLoading(true);
        setError("");
        setMessage("");

        try {

            const response = await fetch(
                api.getTabExportUrl(jobId, tab),
                {
                    method: "GET",
                    cache: "no-store",
                    signal: controller.signal
                }
            );

            if (!response.ok) {

                let detail = "";

                try {
                    const data = await response.json();

                    if (typeof data.detail === "string") {
                        detail = data.detail;
                    }
                } catch {
                    // Use HTTP status as fallback.
                }

                throw new Error(
                    detail ||
                    `Falha na exportacao (HTTP ${response.status}).`
                );

            }

            const contentType =
                response.headers.get("content-type") || "";

            if (!contentType.includes(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )) {

                throw new Error(
                    "O servidor nao retornou um arquivo Excel valido."
                );

            }

            const blob = await response.blob();

            if (blob.size < 4) {
                throw new Error("Arquivo Excel vazio.");
            }

            const signature = new Uint8Array(
                await blob.slice(0, 4).arrayBuffer()
            );

            if (
                signature[0] !== 80 ||
                signature[1] !== 75 ||
                signature[2] !== 3 ||
                signature[3] !== 4
            ) {
                throw new Error(
                    "O arquivo recebido nao possui formato XLSX."
                );
            }

            if (controller.signal.aborted) return;

            const safeId = jobId
                .replace(/[^a-zA-Z0-9_-]/g, "")
                .slice(0, 8);

            const filename =
                `ConciliaAI_${tab}_${safeId}.xlsx`;

            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");

            link.href = url;
            link.download = filename;

            try {
                document.body.appendChild(link);
                link.click();
            } finally {
                link.remove();

                window.setTimeout(() => {
                    URL.revokeObjectURL(url);
                }, 1000);
            }

            setMessage("Arquivo Excel gerado para download.");

        } catch (e) {

            if (!controller.signal.aborted) {

                setError(
                    e instanceof Error
                        ? e.message
                        : String(e)
                );

            }

        } finally {

            if (request.current === controller) {

                request.current = null;
                lock.current = false;

                setLoading(false);

            }

        }

    }

    return (

        <div className="space-y-2">

            <button
                type="button"
                disabled={disabled || loading || !jobId}
                onClick={() => void download()}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-4 py-3 text-sm font-bold text-white shadow-sm hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
            >

                {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin"/>
                ) : (
                    <FileSpreadsheet className="h-4 w-4"/>
                )}

                {loading ? "Gerando Excel..." : label}

            </button>

            {error && (
                <p
                    role="alert"
                    className="text-xs font-semibold text-red-600"
                >
                    {error}
                </p>
            )}

            {message && (
                <p
                    role="status"
                    className="text-xs font-semibold text-emerald-600"
                >
                    {message}
                </p>
            )}

        </div>

    );

}
