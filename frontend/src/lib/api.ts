// Centralized PaperLens API Client Layer

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "https://paperlens-backend-gotx.onrender.com/api/v1";


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
  claim_text: str;
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
  let token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    try {
      const regResp = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: `guest_${Math.random().toString(36).substring(2, 9)}@paperlens.local`,
          password: "GuestPassword123!",
        }),
      });
      if (regResp.ok) {
        const data = await regResp.json();
        token = data.access_token;
        if (token) localStorage.setItem(TOKEN_KEY, token);
      }
    } catch {
      // Ignore registration errors for guest mode fallback
    }
  }
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

  if (response.status === 24) return {} as T;
  return (await response.json()) as T;
}

export async function uploadPaper(file: File): Promise<PaperUploadResponse> {
  const headers = await getAuthHeaders();
  const formData = new FormData();
  formData.append("file", file);

  try {
    const resp = await fetch(`${API_BASE_URL}/papers/upload`, {
      method: "POST",
      headers,
      body: formData,
    });
    return await handleResponse<PaperUploadResponse>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function getPaperStatus(paperId: string): Promise<PaperStatusResponse> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/status`, { headers });
    return await handleResponse<PaperStatusResponse>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function retryPaperPipeline(paperId: string): Promise<any> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/retry`, {
      method: "POST",
      headers,
    });
    return await handleResponse<any>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function getPapers(): Promise<PaperResponse[]> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers`, { headers });
    return await handleResponse<PaperResponse[]>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function getPaper(paperId: string): Promise<PaperResponse> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}`, { headers });
    return await handleResponse<PaperResponse>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function deletePaper(paperId: string): Promise<void> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}`, {
      method: "DELETE",
      headers,
    });
    await handleResponse<void>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function getPaperAnalysis(paperId: string): Promise<PaperAnalysisResponse> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/analysis`, { headers });
    return await handleResponse<PaperAnalysisResponse>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function getPaperMethodology(paperId: string): Promise<MethodologyExtractionResponse> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/methodology`, { headers });
    return await handleResponse<MethodologyExtractionResponse>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function getPaperContributions(
  paperId: string,
): Promise<ContributionExtractionResponse> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/contributions`, { headers });
    return await handleResponse<ContributionExtractionResponse>(resp);
  } catch (err: any) {
    if (!err.status) {
      throw { status: 0, message: "Network error — failed to connect to backend server." };
    }
    throw err;
  }
}

export async function askPaperQuestion(
  paperId: string,
  question: string,
): Promise<QuestionAnsweringResponse> {
  const headers = await getAuthHeaders();
  try {
    const resp = await fetch(`${API_BASE_URL}/papers/${paperId}/questions`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
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
    body: JSON.stringify({ provider, email, name, provider_id: providerId }),
  });
  const data = await handleResponse<any>(resp);
  if (data.access_token) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
  }
  return data;
}

export async function registerUser(email: string, password: string, name?: string): Promise<any> {

  const resp = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  const data = await handleResponse<any>(resp);
  if (data.access_token) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
  }
  return data;
}

export async function getAdminStats(): Promise<any> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/admin/stats`, { headers });
  return await handleResponse<any>(resp);
}

export async function getAdminUsers(): Promise<any[]> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/admin/users`, { headers });
  return await handleResponse<any[]>(resp);
}

export async function deleteAdminUser(userId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const resp = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
    method: "DELETE",
    headers,
  });
  if (!resp.ok) {
    throw await handleResponse<any>(resp);
  }
}

