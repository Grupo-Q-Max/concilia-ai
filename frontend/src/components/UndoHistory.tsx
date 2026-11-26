
"use client";

import React, {
  useState,
  useEffect,
  useCallback,
  useRef
} from "react";

import { getUndoHistoryV5 } from "@/lib/api";

type Props = {
  jobId: string;
  revision: number;
};

type AuditItem = {
  id: string;
  timestamp: string;
  action: string;
  details: any;
};

const fmt = (v: any) =>
  Number(v || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });

const formatDate = (v: string) => {

  const date = new Date(v);

  return Number.isNaN(date.getTime())
    ? v
    : date.toLocaleString("pt-BR");

};

export default function UndoHistory({
  jobId,
  revision
}: Props) {

  const [items, setItems] = useState<AuditItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [limit, setLimit] = useState(30);

  const request = useRef(0);

  const load = useCallback(async () => {

    const seq = ++request.current;

    setLoading(true);
    setError("");

    try {

      const result = await getUndoHistoryV5(jobId);

      if (!Array.isArray(result.items)) {
        throw new Error("Historico retornado em formato invalido.");
      }

      if (seq === request.current) {
        setItems(result.items);
      }

    } catch (e) {

      if (seq === request.current) {

        setItems([]);

        setError(
          e instanceof Error ? e.message : String(e)
        );

      }

    } finally {

      if (seq === request.current) {
        setLoading(false);
      }

    }

  }, [jobId]);

  useEffect(() => {

    void load();

    return () => {
      request.current++;
    };

  }, [load, revision]);

  const totalCents = items.reduce(
    (sum, item) =>
      sum + Math.round(
        Number(item.details?.amount || 0) * 100
      ),
    0
  );

  const filtered = items.filter(item => {

    const d = item.details || {};
    const original = d.original_record || {};

    if (
      filter !== "ALL" &&
      d.origin !== filter
    ) return false;

    const text = [
      original.nf,
      original.supplier,
      original.match_notes,
      original.reason,
      original.payment_trans_id,
      original.invoice_trans_id,
      d.reason,
      d.match_id,
      d.origin,
      item.timestamp
    ].join(" ").toLowerCase();

    return text.includes(
      search.trim().toLowerCase()
    );

  });

  return (

    <details className="border rounded-xl p-4 space-y-4">

      <summary className="cursor-pointer font-bold">

        Historico de desfazimentos
        {" "}({loading ? "..." : items.length})

      </summary>

      <p className="text-xs text-slate-500">

        Auditoria das baixas desfeitas neste documento.
        Os valores representam operacoes historicas,
        nao o saldo atual em aberto.

      </p>

      {error && (

        <div
          role="alert"
          className="border border-red-300 text-red-600 rounded-lg p-3 text-sm"
        >
          {error}
        </div>

      )}

      {loading && (
        <p className="text-sm">Carregando historico...</p>
      )}

      {!loading && !error && (

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

          <div className="border rounded-lg p-3">

            <p className="text-xs text-slate-500">
              Desfazimentos realizados
            </p>

            <p className="text-xl font-bold">
              {items.length}
            </p>

          </div>

          <div className="border rounded-lg p-3">

            <p className="text-xs text-slate-500">
              Valor acumulado restaurado
            </p>

            <p className="text-xl font-bold">
              {fmt(totalCents / 100)}
            </p>

          </div>

        </div>

      )}

      <div className="flex flex-wrap gap-2">

        <input
          value={search}
          placeholder="Buscar NF, motivo ou identificador"
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

          <option value="ALL">Todas as origens</option>
          <option value="CURRENT">Exercicio atual</option>
          <option value="OPENING">Saldo anterior</option>

        </select>

        <button
          disabled={loading}
          onClick={() => void load()}
          className="border rounded-lg px-3 py-2 text-sm"
        >

          Atualizar historico

        </button>

      </div>

      {!loading && !error && !filtered.length && (

        <p className="text-sm text-slate-500">

          Nenhum desfazimento encontrado.

        </p>

      )}

      {!loading && !error && filtered.slice(0, limit).map(item => {

        const d = item.details || {};
        const original = d.original_record || {};

        const restored = Array.isArray(d.restored_transactions)
          ? d.restored_transactions
          : [];

        return (

          <article
            key={item.id}
            className="border rounded-lg p-4 space-y-3"
          >

            <div className="flex flex-wrap justify-between gap-2">

              <div>

                <p className="font-bold">

                  {original.nf
                    ? `NF ${original.nf}`
                    : d.origin === "OPENING"
                      ? "Baixa do saldo anterior"
                      : "Baixa do exercicio"}

                </p>

                <p className="text-xs text-slate-500">

                  {formatDate(item.timestamp)}

                </p>

              </div>

              <div>

                <p className="text-xs text-slate-500">
                  Valor restaurado
                </p>

                <p className="font-bold text-lg">
                  {fmt(d.amount)}
                </p>

              </div>

            </div>

            <p className="text-xs font-semibold text-amber-600">

              Baixa desfeita

            </p>

            <p className="text-sm">

              Origem: {d.origin === "OPENING"
                ? "Saldo anterior"
                : "Exercicio atual"}

            </p>

            {original.supplier && (

              <p className="text-sm">

                Fornecedor: {original.supplier}

              </p>

            )}

            <div className="border rounded-lg p-3">

              <p className="text-xs font-semibold">
                Motivo do desfazimento
              </p>

              <p className="text-sm whitespace-pre-wrap break-words">
                {d.reason || "Nao informado"}
              </p>

            </div>

            {d.opening_remaining != null && (

              <p className="text-sm">

                Saldo anterior restaurado:
                {" "}<b>{fmt(d.opening_remaining)}</b>

              </p>

            )}

            <details className="border rounded-lg p-3">

              <summary className="cursor-pointer text-sm font-semibold">

                Detalhes da auditoria

              </summary>

              <div className="space-y-2 mt-3 text-xs">

                <p className="break-all">
                  Auditoria: {item.id}
                </p>

                <p className="break-all">
                  Baixa original: {d.match_id}
                </p>

                <p>
                  Modalidade: {original.match_type ||
                    (d.origin === "OPENING"
                      ? "OPENING"
                      : "-")}
                </p>

                {restored.map((t: any, i: number) => (

                  <div
                    key={`${t.transaction_id}:${i}`}
                    className="border rounded-lg p-3 space-y-1"
                  >

                    <p className="break-all">
                      Lancamento: {t.transaction_id}
                    </p>

                    <p>
                      Total conciliado apos desfazimento:
                      {" "}{fmt(t.matched_amount)}
                    </p>

                    <p>
                      Saldo residual apos desfazimento:
                      {" "}{fmt(t.remaining_amount)}
                    </p>

                    <p>
                      Status: {t.status}
                    </p>

                  </div>

                ))}

                <details>

                  <summary className="cursor-pointer">
                    Registro original completo
                  </summary>

                  <pre className="overflow-auto text-xs p-2 border rounded-lg mt-2">
                    {JSON.stringify(original, null, 2)}
                  </pre>

                </details>

              </div>

            </details>

          </article>

        );

      })}

      {!loading && !error && filtered.length > limit && (

        <button
          onClick={() => setLimit(v => v + 30)}
          className="border rounded-lg px-4 py-2 text-sm"
        >

          Mostrar mais registros

        </button>

      )}

    </details>

  );

}
