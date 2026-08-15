"use client";

import { useEffect, useState } from "react";
import { listPapers, uploadPaper, ApiError, type Paper } from "@/lib/api";

export default function UploadPanel({ onPapersChange }: { onPapersChange?: (papers: Paper[]) => void }) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    const list = await listPapers();
    setPapers(list);
    onPapersChange?.(list);
  };

  useEffect(() => {
    let cancelled = false;
    listPapers()
      .then((list) => {
        if (cancelled) return;
        setPapers(list);
        onPapersChange?.(list);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load papers");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadPaper(file);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  return (
    <div className="flex h-full flex-col gap-3 border-r border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Papers</h2>
      <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-dashed border-zinc-300 p-4 text-sm text-zinc-600 hover:border-zinc-400 dark:border-zinc-700 dark:text-zinc-400">
        {uploading ? "Uploading…" : "Upload PDF"}
        <input
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
          disabled={uploading}
        />
      </label>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <ul className="flex flex-col gap-2 overflow-y-auto">
        {papers.map((p) => (
          <li key={p.paper_id} className="rounded-md bg-zinc-100 p-2 text-sm dark:bg-zinc-900">
            <div className="truncate font-medium" title={p.filename}>
              {p.filename}
            </div>
            <div className="text-xs text-zinc-500">
              {p.num_pages} pages · {p.num_chunks} chunks
            </div>
          </li>
        ))}
        {papers.length === 0 && <li className="text-xs text-zinc-400">No papers indexed yet.</li>}
      </ul>
    </div>
  );
}
