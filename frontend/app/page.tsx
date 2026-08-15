"use client";

import { useState } from "react";
import Link from "next/link";
import ChatWindow from "@/components/ChatWindow";
import UploadPanel from "@/components/UploadPanel";
import type { Paper } from "@/lib/api";

export default function Home() {
  const [papers, setPapers] = useState<Paper[]>([]);

  return (
    <div className="flex h-screen">
      <aside className="w-72 flex-shrink-0">
        <UploadPanel onPapersChange={setPapers} />
      </aside>
      <main className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-zinc-200 p-3 dark:border-zinc-800">
          <h1 className="font-semibold">Research Paper Digest</h1>
          <Link href="/eval" className="text-xs text-blue-600 hover:underline">
            Eval dashboard →
          </Link>
        </header>
        <ChatWindow hasPapers={papers.length > 0} />
      </main>
    </div>
  );
}
