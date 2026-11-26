// CONCILIA_V5_REFRESH_CENTER_23C

import { api } from "@/lib/api";

export interface RefreshTicketV5 {
    jobId: string;
    revision: number;
}

export function createRefreshCenterV5() {

    let activeJob: string | null = null;
    let revision = 0;

    return {

        begin(jobId: string): RefreshTicketV5 {

            activeJob = jobId;
            revision += 1;

            return {
                jobId,
                revision
            };

        },

        invalidate() {

            activeJob = null;
            revision += 1;

        },

        isCurrent(ticket: RefreshTicketV5): boolean {

            return (
                ticket.jobId === activeJob &&
                ticket.revision === revision
            );

        }

    };

}

export async function fetchJobSnapshotV5(
    jobId: string
) {

    const [
        summary,
        reconciled,
        open,
        divergences,
        suppliers
    ] = await Promise.all([

        api.getSummary(jobId),
        api.getReconciled(jobId),
        api.getOpen(jobId),
        api.getDivergences(jobId),
        api.getSupplierSummary(jobId)

    ]);

    if (
        !summary ||
        summary.job?.id !== jobId ||
        !summary.summary ||
        !Array.isArray(reconciled) ||
        !Array.isArray(open) ||
        !Array.isArray(suppliers) ||
        !Array.isArray(divergences?.divergent_pairs) ||
        !Array.isArray(divergences?.unmapped_debits)
    ) {

        throw new Error(
            "Resposta incompleta ou documento incorreto."
        );

    }

    return {

        jobId,
        summary,
        reconciled,
        open,
        divergences,
        suppliers,
        refreshedAt: new Date().toISOString()

    };

}

export const REFRESH_EVENT_V5 =
    "concilia:refresh:v5";

export interface RefreshEventV5 {

    jobId: string;
    source: string;

}

export function notifyRefreshV5(
    jobId: string,
    source: string
) {

    if (typeof window === "undefined") return;

    window.dispatchEvent(
        new CustomEvent<RefreshEventV5>(
            REFRESH_EVENT_V5,
            {
                detail: {
                    jobId,
                    source
                }
            }
        )
    );

}

export function subscribeRefreshV5(
    jobId: string,
    callback: (event: RefreshEventV5) => void
): () => void {

    if (typeof window === "undefined") {
        return () => {};
    }

    const listener = (event: Event) => {

        const detail = (
            event as CustomEvent<RefreshEventV5>
        ).detail;

        if (detail?.jobId !== jobId) return;

        callback(detail);

    };

    window.addEventListener(
        REFRESH_EVENT_V5,
        listener
    );

    return () => {

        window.removeEventListener(
            REFRESH_EVENT_V5,
            listener
        );

    };

}
