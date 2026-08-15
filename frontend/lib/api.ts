const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new ApiError(detail, res.status);
  }

  return res.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
  index_loaded?: boolean;
  num_chunks?: number;
  num_papers?: number;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export interface Paper {
  paper_id: string;
  filename: string;
  num_pages: number;
  num_chunks: number;
}

export function listPapers(): Promise<Paper[]> {
  return request<Paper[]>("/api/papers");
}

export interface UploadResponse {
  paper_id: string;
  filename: string;
  num_pages: number;
  num_chunks: number;
  status: string;
}

export function uploadPaper(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<UploadResponse>("/api/upload", { method: "POST", body: formData });
}

export interface SourceChunk {
  chunk_id: string;
  paper_id: string;
  page: number;
  section: string | null;
  snippet: string;
}

export interface QueryResponse {
  query_id: string;
  answer: string;
  sources: SourceChunk[];
  route_type: "single_fact" | "multi_part" | "summarization";
  sub_queries: string[];
  ragas: { faithfulness: number | null; answer_relevancy: number | null } | null;
  ragas_pending: boolean;
  latency_ms: { pipeline_total: number };
}

export function askQuestion(question: string): Promise<QueryResponse> {
  return request<QueryResponse>("/api/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export interface EvalLogEntry {
  timestamp: string;
  query_id: string;
  question: string;
  answer_preview: string;
  route_type: string;
  num_sub_queries: number;
  retrieved_chunk_ids: string[];
  faithfulness: number | null;
  answer_relevancy: number | null;
  context_precision: number | null;
  context_precision_source: string | null;
  latency_ms: Record<string, number>;
  generation_model?: string;
  judge_model?: string;
}

export function getEvalLogs(limit = 50): Promise<EvalLogEntry[]> {
  return request<EvalLogEntry[]>(`/api/eval/logs?limit=${limit}`);
}

export interface RerankLogEntry {
  timestamp: string;
  query_id: string;
  question: string;
  pre_rerank_order: { chunk_id: string; page: number; faiss_score: number; rank: number }[];
  post_rerank_order: { chunk_id: string; page: number; cross_encoder_score: number; rank: number }[];
  rank_changes: { chunk_id: string; old_rank: number; new_rank: number }[];
}

export function getRerankLog(limit = 20): Promise<RerankLogEntry[]> {
  return request<RerankLogEntry[]>(`/api/eval/rerank-log?limit=${limit}`);
}

export interface GoldenEvalItem {
  timestamp: string;
  question: string;
  answer_preview: string;
  route_type: string;
  faithfulness: number | null;
  answer_relevancy: number | null;
  context_precision: number | null;
}

export interface GoldenEvalResponse {
  aggregate: {
    faithfulness: number | null;
    answer_relevancy: number | null;
    context_precision: number | null;
    num_items: number;
  };
  per_item: GoldenEvalItem[];
}

export function runGoldenEval(): Promise<GoldenEvalResponse> {
  return request<GoldenEvalResponse>("/api/eval/run", { method: "POST" });
}
