"use client";

import { useEffect, useState } from "react";
import { getEvalLogs } from "@/lib/api";

type Scores = { faithfulness: number | null; answer_relevancy: number | null };

function scoreColor(score: number): string {
  if (score >= 0.7) return "bg-green-100 text-green-800";
  if (score >= 0.4) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

/** RAGAS scoring runs in a backend background task (see PROGRESS.md) so the
 * answer isn't held up by it -- this polls the eval log briefly until the
 * score for this query shows up, then stops. */
export default function EvalBadge({ queryId }: { queryId: string }) {
  const [scores, setScores] = useState<Scores | null>(null);
  const [givenUp, setGivenUp] = useState(false);

  useEffect(() => {
    let attempts = 0;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const maxAttempts = 12; // ~60s at 5s intervals

    const poll = async () => {
      attempts += 1;
      try {
        const logs = await getEvalLogs(20);
        const match = logs.find((l) => l.query_id === queryId);
        if (match && !cancelled) {
          setScores({ faithfulness: match.faithfulness, answer_relevancy: match.answer_relevancy });
          return;
        }
      } catch {
        // ignore transient errors, just retry
      }
      if (cancelled) return;
      if (attempts >= maxAttempts) {
        setGivenUp(true);
        return;
      }
      timer = setTimeout(poll, 5000);
    };

    timer = setTimeout(poll, 3000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [queryId]);

  if (givenUp) return null;
  if (!scores) return <span className="text-xs italic text-zinc-400">scoring…</span>;

  return (
    <div className="flex gap-1.5 text-xs">
      {scores.faithfulness !== null && (
        <span className={`rounded px-1.5 py-0.5 ${scoreColor(scores.faithfulness)}`}>
          faithfulness {scores.faithfulness.toFixed(2)}
        </span>
      )}
      {scores.answer_relevancy !== null && (
        <span className={`rounded px-1.5 py-0.5 ${scoreColor(scores.answer_relevancy)}`}>
          relevancy {scores.answer_relevancy.toFixed(2)}
        </span>
      )}
    </div>
  );
}
