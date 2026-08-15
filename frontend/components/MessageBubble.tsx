import EvalBadge from "./EvalBadge";
import SourcesPanel from "./SourcesPanel";
import type { ChatMessage } from "./ChatWindow";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
          isUser ? "bg-blue-600 text-white" : "bg-zinc-100 dark:bg-zinc-900"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm">{message.content}</p>

        {!isUser && message.sources && <SourcesPanel sources={message.sources} />}

        {!isUser && message.routeType === "multi_part" && (message.subQueries?.length ?? 0) > 1 && (
          <p className="mt-1.5 text-xs text-zinc-400">Decomposed into: {message.subQueries!.join(" · ")}</p>
        )}

        {!isUser && message.queryId && (
          <div className="mt-1.5">
            <EvalBadge queryId={message.queryId} />
          </div>
        )}
      </div>
    </div>
  );
}
