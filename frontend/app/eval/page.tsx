"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getEvalLogs,
  getRerankLog,
  runGoldenEval,
  type EvalLogEntry,
  type GoldenEvalResponse,
  type RerankLogEntry,
} from "@/lib/api";

function fmt(n: number | null): string {
  return n === null ? "—" : n.toFixed(3);
}

export default function EvalDashboard() {
  const [logs, setLogs] = useState<EvalLogEntry[]>([]);
  const [rerankLog, setRerankLog] = useState<RerankLogEntry[]>([]);
  const [goldenResult, setGoldenResult] = useState<GoldenEvalResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    getEvalLogs(20).then(setLogs).catch(() => {});
    getRerankLog(10).then(setRerankLog).catch(() => {});
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleRunGolden = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await runGoldenEval();
      setGoldenResult(result);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Golden eval failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Evaluation Dashboard</h1>
        <Link href="/" className="text-sm text-blue-600 hover:underline">
          ← Back to chat
        </Link>
      </div>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-medium">Golden Set Evaluation (includes context_precision)</h2>
          <button
            onClick={handleRunGolden}
            disabled={running}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white disabled:opacity-40"
          >
            {running ? "Running… (can take a minute or two)" : "Run golden eval"}
          </button>
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
        {goldenResult && (
          <div className="flex flex-wrap gap-4 rounded-lg bg-zinc-50 p-3 text-sm dark:bg-zinc-900">
            <span>
              faithfulness: <strong>{fmt(goldenResult.aggregate.faithfulness)}</strong>
            </span>
            <span>
              answer_relevancy: <strong>{fmt(goldenResult.aggregate.answer_relevancy)}</strong>
            </span>
            <span>
              context_precision: <strong>{fmt(goldenResult.aggregate.context_precision)}</strong>
            </span>
            <span>n={goldenResult.aggregate.num_items}</span>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 font-medium">Recent Query Evaluations</h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-zinc-500 dark:border-zinc-800">
                <th className="py-1.5 pr-3">Question</th>
                <th className="py-1.5 pr-3">Route</th>
                <th className="py-1.5 pr-3">Faithfulness</th>
                <th className="py-1.5 pr-3">Relevancy</th>
                <th className="py-1.5 pr-3">Context Precision</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l, idx) => (
                <tr key={l.query_id ?? `${l.timestamp}-${idx}`} className="border-b border-zinc-100 dark:border-zinc-900">
                  <td className="max-w-xs truncate py-1.5 pr-3" title={l.question}>
                    {l.question}
                  </td>
                  <td className="py-1.5 pr-3">{l.route_type}</td>
                  <td className="py-1.5 pr-3">{fmt(l.faithfulness)}</td>
                  <td className="py-1.5 pr-3">{fmt(l.answer_relevancy)}</td>
                  <td className="py-1.5 pr-3">{fmt(l.context_precision)}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-3 text-zinc-400">
                    No queries logged yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-2 font-medium">Re-ranking: Before / After</h2>
        <div className="flex flex-col gap-3">
          {rerankLog.map((r) => (
            <div key={r.query_id} className="rounded-lg border border-zinc-200 p-3 text-sm dark:border-zinc-800">
              <p className="mb-1 font-medium">{r.question}</p>
              <p className="mb-2 text-xs text-zinc-500">
                {r.rank_changes.length} of {r.pre_rerank_order.length} chunks changed rank
              </p>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="mb-1 text-zinc-400">Before (FAISS)</p>
                  <ol className="list-inside list-decimal">
                    {r.pre_rerank_order.slice(0, 5).map((c) => (
                      <li key={c.chunk_id} className="truncate">
                        {c.chunk_id} (p.{c.page})
                      </li>
                    ))}
                  </ol>
                </div>
                <div>
                  <p className="mb-1 text-zinc-400">After (cross-encoder)</p>
                  <ol className="list-inside list-decimal">
                    {r.post_rerank_order.slice(0, 5).map((c) => (
                      <li key={c.chunk_id} className="truncate">
                        {c.chunk_id} (p.{c.page})
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          ))}
          {rerankLog.length === 0 && <p className="text-sm text-zinc-400">No queries logged yet.</p>}
        </div>
      </section>
    </div>
  );
}
