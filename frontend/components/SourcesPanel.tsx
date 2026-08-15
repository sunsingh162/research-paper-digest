"use client";

import { useState } from "react";
import type { SourceChunk } from "@/lib/api";

export default function SourcesPanel({ sources }: { sources: SourceChunk[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (sources.length === 0) return null;

  const active = sources.find((s) => s.chunk_id === expanded);

  return (
    <div className="mt-2">
      <div className="flex flex-wrap gap-1.5">
        {sources.map((s) => (
          <button
            key={s.chunk_id}
            onClick={() => setExpanded(expanded === s.chunk_id ? null : s.chunk_id)}
            className="rounded-full border border-zinc-300 px-2 py-0.5 text-xs hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            {s.paper_id} · p.{s.page}
            {s.section ? ` · §${s.section}` : ""}
          </button>
        ))}
      </div>
      {active && (
        <div className="mt-1.5 rounded-md border border-zinc-200 bg-zinc-50 p-2 text-xs text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
          {active.snippet}
        </div>
      )}
    </div>
  );
}
