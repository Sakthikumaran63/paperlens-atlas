// Centralized PaperLens API Client Layer

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api/v1";



const TOKEN_KEY = "paperlens_access_token";

export interface ApiError {
  status: number;
  message: string;
  detail?: any;
}

export interface PaperUploadResponse {
  paper_id: string;
  file_name: string;
  status: "UPLOADED" | "PROCESSING" | "READY" | "FAILED";
}

export interface PaperStatusResponse {
  paper_id: string;
  status: "UPLOADED" | "PROCESSING" | "READY" | "FAILED";
  stage:
    | "UPLOADING"
    | "EXTRACTING"
    | "STRUCTURING"
    | "CHUNKING"
    | "EMBEDDING"
    | "ANALYZING"
    | "READY"
    | "FAILED";
  progress: number;
  stages_detail?: Record<
    string,
    { status: string; start_time?: string; end_time?: string; error?: string }
  >;
  processing_error?: string;
}

export interface PaperResponse {
  id: string;
  workspace_id: string;
  title: string;
  authors?: string;
  abstract?: string;
  publication_year?: number;
  file_name: string;
  file_size: number;
  page_count: number;
  status: "UPLOADED" | "PROCESSING" | "READY" | "FAILED";
  stage:
    | "UPLOADING"
    | "EXTRACTING"
    | "STRUCTURING"
    | "CHUNKING"
    | "EMBEDDING"
    | "ANALYZING"
    | "READY"
    | "FAILED";
  progress: number;
  processing_error?: string;
  created_at: string;
  updated_at: string;
}

export interface ClaimWithSource {
  claim_id: string;
  claim_text: string;
  section: string;
  page: number;
}

export interface StructuredPaperSummary {
  executive_summary: string;
  problem_statement: string;
  objective: string;
  methodology_summary: string;
  key_contributions: string[];
  dataset: string;
  experimental_setup: string;
  key_results: string;
  limitations: string;
  conclusion: string;
}

export interface PaperAnalysisResponse {
  id: string;
  paper_id: string;
  summary: StructuredPaperSummary;
  claims: ClaimWithSource[];
  created_at: string;
}

export interface MethodologyEvidenceItem {
  evidence_id: string;
  section: string;
  page: number;
  text: string;
}

export interface MethodologyExtractionResponse {
  approach?: string;
  model?: string;
  algorithms?: string;
  dataset?: string;
  preprocessing?: string;
  training?: string;
  experimental_setup?: string;
  metrics: string[];
  evidence: MethodologyEvidenceItem[];
}

export interface ContributionEvidence {
  page: number;
  section: string;
  chunk_id: string;
}

export interface ExtractedContribution {
  text: string;
  contribution_type: "EXPLICIT" | "INFERRED";
  evidence: ContributionEvidence;
}

export interface ContributionExtractionResponse {
  contributions: ExtractedContribution[];
}

export interface SourceMetadataItem {
  page: number;
  section: string;
  chunk_id: string;
  text: string;
}

export interface QuestionAnsweringResponse {
  question_id: string;
  question: string;
  question_type: string;
  answer: string;
  abstained: boolean;
  support_score: number;
  sources: SourceMetadataItem[];
}

async function getAuthHeaders(): Promise<HeadersInit> {
  const token = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail: any = null;
    try {
      errorDetail = await response.json();
    } catch {
      // Body not JSON
    }

    let msg = `HTTP ${response.status}: Request failed`;
    if (errorDetail && errorDetail.detail) {
      msg =
        typeof errorDetail.detail === "string"
          ? errorDetail.detail
          : JSON.stringify(errorDetail.detail);
    } else if (response.status === 413) {
      msg = "File size exceeds the maximum limit of 20MB.";
    } else if (response.status === 429) {
      msg = "Too many requests. Please wait a moment and try again.";
    } else if (response.status === 500) {
      msg = "Internal server error. Please try again later.";
    }

    const err: ApiError = {
      status: response.status,
      message: msg,
      detail: errorDetail,
    };
    throw err;
  }

  const text = await response.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

export async function getMe(): Promise<any> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/auth/me`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<any>(resp);
}

export async function logoutUser(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Ignore network error on logout
  }
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("paperlens_user");
  }
}

export async function getPapers(): Promise<PaperResponse[]> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<PaperResponse[]>(resp);
}

export interface RetrievalMetrics {
  recall_at_k: number;
  precision_at_k: number;
  mrr: number;
}

export interface GroundingMetrics {
  evidence_precision: number;
  evidence_recall: number;
  unsupported_claim_rate: number;
}

export interface AbstentionMetrics {
  answerable_accuracy: number;
  unanswerable_detection: number;
  false_answer_rate: number;
}

export interface ConfigurationEvalReport {
  config_name: string;
  total_questions: number;
  answerable_count: number;
  unanswerable_count: number;
  retrieval: RetrievalMetrics;
  grounding: GroundingMetrics;
  abstention: AbstentionMetrics;
}

export interface EvaluationBenchmarkReport {
  benchmark_id: string;
  timestamp: string;
  configurations: ConfigurationEvalReport[];
}

export interface SystemHealthResponse {
  status: string;
  environment: string;
  database: string;
  ai_service: string;
  version?: string;
  uptime?: string;
}

export async function getPaperDetail(paperId: string): Promise<PaperResponse> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<PaperResponse>(resp);
}

export const getPaper = getPaperDetail;

export async function evaluatePaperBenchmark(paperId: string): Promise<EvaluationBenchmarkReport> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/evaluate`, {
    method: "POST",
    headers,
    credentials: "include",
  });
  return await handleResponse<EvaluationBenchmarkReport>(resp);
}

export async function getSystemHealth(): Promise<SystemHealthResponse> {
  const resp = await fetch(`${API_BASE_URL}/health`);
  return await handleResponse<SystemHealthResponse>(resp);
}

export async function getPaperStatus(paperId: string): Promise<PaperStatusResponse> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/status`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<PaperStatusResponse>(resp);
}

export async function retryPaperPipeline(paperId: string): Promise<any> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/retry`, {
    method: "POST",
    headers,
    credentials: "include",
  });
  return await handleResponse<any>(resp);
}

export async function reanalyzePaper(paperId: string): Promise<any> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/reanalyze`, {
    method: "POST",
    headers,
    credentials: "include",
  });
  return await handleResponse<any>(resp);
}

export async function uploadPaper(file: File, workspaceId?: string): Promise<PaperUploadResponse> {
  const headers = await getAuthHeaders();
  const formData = new FormData();
  formData.append("file", file);
  if (workspaceId) {
    formData.append("workspace_id", workspaceId);
  }

  const resp = await fetch(`${API_BASE_URL}/papers/upload`, {
    method: "POST",
    headers,
    credentials: "include",
    body: formData,
  });
  return await handleResponse<PaperUploadResponse>(resp);
}

export async function deletePaper(paperId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}`, {
    method: "DELETE",
    headers,
    credentials: "include",
  });
  if (!resp.ok) {
    throw await handleResponse<any>(resp);
  }
}

export async function getPaperAnalysis(paperId: string): Promise<PaperAnalysisResponse> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/analysis`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<PaperAnalysisResponse>(resp);
}

export async function getPaperMethodology(paperId: string): Promise<MethodologyExtractionResponse> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/methodology`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<MethodologyExtractionResponse>(resp);
}

export async function getPaperContributions(paperId: string): Promise<ContributionExtractionResponse> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/contributions`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<ContributionExtractionResponse>(resp);
}

export async function askPaperQuestion(
  paperId: string,
  question: string
): Promise<QuestionAnsweringResponse> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/questions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      credentials: "include",
      body: JSON.stringify({ question }),
    });
    return await handleResponse<QuestionAnsweringResponse>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function oauthLogin(provider: "google" | "microsoft", email: string, name?: string, providerId?: string): Promise<any> {
  const resp = await fetch(`${API_BASE_URL}/auth/oauth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ provider, email, name, provider_id: providerId }),
  });
  const data = await handleResponse<any>(resp);
  if (data.access_token && typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, data.access_token);
  }
  return data;
}

export async function registerUser(email: string, password: string, name?: string): Promise<any> {
  const resp = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password, name }),
  });
  const data = await handleResponse<any>(resp);
  if (data.access_token && typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, data.access_token);
  }
  return data;
}

export async function getAdminStats(): Promise<any> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/admin/stats`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<any>(resp);
}

export async function getAdminUsers(): Promise<any[]> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/admin/users`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<any[]>(resp);
}

export async function deleteAdminUser(userId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
    method: "DELETE",
    headers,
    credentials: "include",
  });
  if (!resp.ok) {
    throw await handleResponse<any>(resp);
  }
}

export async function getPaperChatHistory(paperId: string): Promise<QuestionAnsweringResponse[]> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/chat-history`, {
    headers,
    credentials: "include",
  });
  return await handleResponse<QuestionAnsweringResponse[]>(resp);
}

export interface RecommendedPaper {
  title: string;
  year?: number;
  abstract?: string;
  authors: string[];
  url?: string;
}

export interface PaperRecommendationsResponse {
  seed_paper_id?: string;
  seed_title: string;
  count: number;
  recommendations: RecommendedPaper[];
}

export async function getPaperRecommendations(
  paperId: string,
  limit: number = 5
): Promise<PaperRecommendationsResponse> {
  const headers = await getAuthHeaders();
  const resp = await fetch(
    `${API_BASE_URL}/papers/${paperId}/recommendations?limit=${limit}`,
    {
      headers,
      credentials: "include",
    }
  );
  return await handleResponse<PaperRecommendationsResponse>(resp);
}

export async function searchPaperRecommendations(
  title: string,
  limit: number = 5
): Promise<PaperRecommendationsResponse> {
  const headers = await getAuthHeaders();
  const resp = await fetch(
    `${API_BASE_URL}/papers/recommendations/search?title=${encodeURIComponent(title)}&limit=${limit}`,
    {
      headers,
      credentials: "include",
    }
  );
  return await handleResponse<PaperRecommendationsResponse>(resp);
}


