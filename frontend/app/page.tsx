"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";

type Status = "checking" | "online" | "offline";

export default function Home() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    getHealth()
      .then(() => setStatus("online"))
      .catch(() => setStatus("offline"));
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-50 font-sans dark:bg-black">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Research Paper Digest</h1>
      <p className="text-zinc-600 dark:text-zinc-400">RAG assistant scaffold — backend status:</p>
      <span
        className={`rounded-full px-3 py-1 text-sm font-medium ${
          status === "online"
            ? "bg-green-100 text-green-800"
            : status === "offline"
              ? "bg-red-100 text-red-800"
              : "bg-zinc-200 text-zinc-700"
        }`}
      >
        {status}
      </span>
    </div>
  );
}
