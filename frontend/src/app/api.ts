// API configuration 
// All data access is via the backend REST API
// No direct database client usage in frontend for security

import { supabase } from "@/lib/supabaseClient";
import { notifyUnauthorized } from "@/lib/authEvents";

// API設定
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// デバッグ用ログ
console.log('=== API Configuration ===');
console.log('API_BASE_URL:', API_BASE_URL);
console.log('Environment:', {
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NODE_ENV: process.env.NODE_ENV,
});
console.log('=====================');

// 共通のfetch関数（エラーハンドリング付き）
const apiFetch = async (url: string, options?: RequestInit) => {
  const fullUrl = `${API_BASE_URL}${url}`;
  console.log('Fetching:', fullUrl, options);

  // 現在のSupabaseセッションからアクセストークンを取得し、Authorizationヘッダーに付与する
  const { data: { session } } = await supabase.auth.getSession();
  const authHeaders: Record<string, string> = session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};

  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options?.headers,
      },
    });
    
    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', response.status, errorText);
      if (response.status === 401) {
        // 401 の詳細をログ出力（デバッグ用）
        console.error('[api] 401 Unauthorized - details:', {
          url: fullUrl,
          hadAuthHeader: !!authHeaders.Authorization,
          errorText,
        });
        
        // "Authentication is not configured" はバックエンドの環境変数ミスを示す
        // この場合はサインアウトせずエラーを投げるのみ
        if (errorText.includes('Authentication is not configured')) {
          console.error('[api] Backend SUPABASE_JWT_SECRET is not configured on Vercel');
          throw new Error('サーバー認証設定エラー: バックエンドの環境変数を確認してください');
        }
        
        // トークンが失効/不正: ログイン画面に戻す
        notifyUnauthorized();
      }
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }
    
    // レスポンスの内容をデバッグ
    const responseText = await response.text();
    console.log('Response text (first 200 chars):', responseText.substring(0, 200));
    
    // テキストをJSONとしてパース
    try {
      const jsonData = JSON.parse(responseText);
      console.log('Parsed JSON data:', jsonData);
      return jsonData; // 直接JSONデータを返す
    } catch (parseError) {
      console.error('JSON parse error:', parseError);
      console.error('Full response text:', responseText);
      throw new Error(`Invalid JSON response: ${responseText.substring(0, 100)}`);
    }
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
};

// セッション関連API
export const sessionAPI = {
  // セッション一覧取得
  getSessions: async () => {
    // backend API 経由で取得（移行後はこちらを推奨）
    return await apiFetch('/sessions');
  },

  // セッション作成
  createSession: async (name?: string) => {
    return await apiFetch('/sessions', {
      method: 'POST',
      body: JSON.stringify({ name: name || '新しいセッション' })
    });
  },

  // セッション削除
  deleteSession: async (sessionId: string) => {
    return await apiFetch(`/sessions/${sessionId}`, {
      method: 'DELETE'
    });
  },

  // セッション更新
  updateSession: async (sessionId: string, updates: Record<string, unknown>) => {
    return await apiFetch(`/sessions/${sessionId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  },

  // セッション詳細取得
  getSessionById: async (sessionId: string) => {
    return await apiFetch(`/sessions/${sessionId}`);
  }
};

export type HistoryStatus = 'pending' | 'confirmed' | 'failed';

export type HistoryAPIResponse = {
  historyId: string;
  sessionId: string;
  timestamp?: string;
  originalText: string;
  instructionPrompt?: string;
  targetText: string;
  combinedComment?: string;
  selectedProposalIds?: string;
  customProposals?: string;
  status?: HistoryStatus;
  overallComment?: string;
  provider?: string;
  /** Inference provenance, distinct from `provider` (the transport). */
  llmProvider?: string | null;
  llmModel?: string | null;
  clientJobId?: string;
};

// 履歴関連API
export const historyAPI = {
  // セッションの履歴一覧取得
  getHistories: async (sessionId: string): Promise<HistoryAPIResponse[]> => {
    return await apiFetch(`/sessions/${sessionId}/histories`);
  },

  // 履歴作成（生成直後は status=pending、従来の確定保存は confirmed 既定）
  createHistory: async (historyData: {
    sessionId: string;
    originalText: string;
    targetText: string;
    instructionPrompt?: string;
    combinedComment?: string;
    selectedProposalIds?: string;
    customProposals?: string;
    status?: HistoryStatus;
    overallComment?: string;
    provider?: string;
    llmProvider?: string;
    llmModel?: string;
    clientJobId?: string;
  }) => {
    return await apiFetch('/histories', {
      method: 'POST',
      body: JSON.stringify(historyData)
    });
  },

  // pending → confirmed など、同一生成ラウンドの更新（二重 INSERT を避ける）
  updateHistory: async (
    historyId: string,
    updates: {
      status?: HistoryStatus;
      combinedComment?: string;
      overallComment?: string;
      selectedProposalIds?: string;
      customProposals?: string;
      provider?: string;
      clientJobId?: string;
      instructionPrompt?: string;
    },
  ) => {
    return await apiFetch(`/histories/${historyId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  },

  // 履歴のアーカイブ（ソフトデリート、セッション削除と同じパターン）
  archiveHistory: async (historyId: string) => {
    return await apiFetch(`/histories/${historyId}`, {
      method: 'DELETE'
    });
  }
};

// 提案関連API
export const proposalAPI = {
  // 履歴の提案一覧取得
  getProposals: async (historyId: string) => {
    return await apiFetch(`/histories/${historyId}/proposals`);
  },

  // 提案作成
  createProposal: async (proposalData: {
    historyId: string;
    type: 'AI' | 'Custom';
    originalAfterText: string;
    originalReason?: string;
    modifiedAfterText?: string;
    modifiedReason?: string;
    isSelected: boolean;
    isModified: boolean;
    isCustom?: boolean;
    selectedOrder?: number;
  }) => {
    return await apiFetch('/proposals', {
      method: 'POST',
      body: JSON.stringify(proposalData)
    });
  },

  // 確定時の選択/編集フラグ更新（既存 AI 提案の二重作成を避ける）
  updateProposal: async (
    proposalId: string,
    updates: {
      isSelected?: boolean;
      isModified?: boolean;
      isCustom?: boolean;
      selectedOrder?: number | null;
      modifiedAfterText?: string;
      modifiedReason?: string;
      originalAfterText?: string;
      originalReason?: string;
      type?: 'AI' | 'Custom';
    },
  ) => {
    return await apiFetch(`/proposals/${proposalId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  },
};

// 添削プロンプト設定API（全ユーザー共通の1レコード、DBで永続化）
export type PromptSettingsResponse = {
  /** Effective prompt: the stored custom body, or the built-in default. */
  systemPrompt: string;
  /** Built-in default body, for the reset-to-default comparison. */
  defaultSystemPrompt: string;
  isCustomized: boolean;
  /** Attribution of the stored prompt; null when the default is in effect. */
  updatedAt?: string | null;
  updatedBy?: string | null;
};

export const settingsAPI = {
  getPrompt: async (): Promise<PromptSettingsResponse> => {
    return await apiFetch('/settings/prompt');
  },

  updatePrompt: async (systemPrompt: string): Promise<PromptSettingsResponse> => {
    return await apiFetch('/settings/prompt', {
      method: 'PUT',
      body: JSON.stringify({ systemPrompt }),
    });
  },

  // Deletes the stored row so the built-in default applies again — which is
  // why a later improvement to the default still reaches everyone.
  resetPrompt: async (): Promise<PromptSettingsResponse> => {
    return await apiFetch('/settings/prompt', {
      method: 'DELETE',
    });
  },
};

// AI提案生成API
// Primary: Cloud LLM (Groq/Cloudflare) via backend.
// WebLLM is NOT an automatic fallback — only when the user enables オフラインモード.
export type SuggestionsResponse = {
  suggestions: Array<{
    id: string;
    original: string;
    reason: string;
    // Optional excerpt from SOURCE TEXT corresponding to `original` (a
    // flagged TARGET TEXT excerpt). Empty/absent when the model found no
    // clear correspondence — see highlight-suggestion-text-spans change.
    sourceExcerpt?: string;
  }>;
  overallComment: string;
  /** Inference provider that answered: gemini | groq | cloudflare. */
  llmProvider?: string | null;
  /** Exact model id, e.g. gemini-3.7-flash (providers rotate per request). */
  llmModel?: string | null;
};

export type SuggestionsErrorResponse = {
  error: string;
  fallback_available: boolean;
  message?: string;
  gemini_error?: string;
  groq_error?: string;
  cf_error?: string;
  /** True when cloud providers failed due to rate-limit / quota / cooldown. */
  rate_limited?: boolean;
  /** True when the failover chain ran out of its wall-clock budget. */
  timed_out?: boolean;
  /** Loaded credential counts (no secrets) for ops diagnosis. */
  gemini_pool_size?: number;
  groq_pool_size?: number;
  cf_pool_size?: number;
};

/**
 * Per-provider breakdown of a cloud-suggestions failure, for display.
 *
 * The backend already returns why each provider declined and how many
 * credentials it loaded; without this the UI showed only "全プロバイダ失敗",
 * which cannot distinguish an unset key from an exhausted quota from a timeout.
 */
export function describeProviderFailures(
  body: SuggestionsErrorResponse | null,
): string {
  if (!body) return "";
  const providers: Array<[string, string | undefined, number | undefined]> = [
    ["Gemini", body.gemini_error, body.gemini_pool_size],
    ["Groq", body.groq_error, body.groq_pool_size],
    ["Cloudflare", body.cf_error, body.cf_pool_size],
  ];
  return providers
    .filter(([, error]) => !!error)
    .map(([name, error, poolSize]) => `${name}（鍵${poolSize ?? 0}件）: ${error}`)
    .join(" / ");
}

/** Append the provider breakdown to a user-facing failure message. */
export function withProviderDetail(message: string, detail: string): string {
  return detail ? `${message}\n内訳: ${detail}` : message;
}

/** Structured cloud-suggestions failure (quota/rate-limit visible to UI). */
export class SuggestionsAPIError extends Error {
  status: number;
  rateLimited: boolean;
  body: SuggestionsErrorResponse | null;
  /** Per-provider breakdown ("" when the response carried none). */
  providerDetail: string;

  constructor(
    status: number,
    body: SuggestionsErrorResponse | null,
    fallbackMessage: string,
  ) {
    const msg =
      body?.message ||
      body?.error ||
      fallbackMessage;
    super(msg);
    this.name = "SuggestionsAPIError";
    this.status = status;
    this.body = body;
    this.providerDetail = describeProviderFailures(body);
    const haystack = [
      body?.message,
      body?.error,
      body?.gemini_error,
      body?.groq_error,
      body?.cf_error,
      fallbackMessage,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    this.rateLimited =
      !!body?.rate_limited ||
      /rate.?limit|quota|cooldown|exhausted|429/.test(haystack);
  }
}

export function isSuggestionsAPIError(err: unknown): err is SuggestionsAPIError {
  return err instanceof SuggestionsAPIError;
}

export const suggestionsAPI = {
  // Generate AI suggestions via backend (Groq/Cloudflare).
  // Uses a dedicated fetch path so 503 bodies (rate_limited / message) are
  // preserved for the UI — unlike the generic apiFetch Error string.
  // `exemplarTranslation` (模範回答訳文) is optional reference calibration.
  // The key is omitted entirely when blank so the request body — and therefore
  // the prompt the backend builds — is unchanged for users without an exemplar.
  generate: async (
    originalText: string,
    targetText: string,
    exemplarTranslation?: string,
  ): Promise<SuggestionsResponse> => {
    const fullUrl = `${API_BASE_URL}/suggestions`;
    const { data: { session } } = await supabase.auth.getSession();
    const authHeaders: Record<string, string> = session?.access_token
      ? { Authorization: `Bearer ${session.access_token}` }
      : {};

    const trimmedExemplar = (exemplarTranslation || "").trim();

    let response: Response;
    try {
      response = await fetch(fullUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders,
        },
        body: JSON.stringify({
          originalText,
          targetText,
          ...(trimmedExemplar ? { exemplarTranslation: trimmedExemplar } : {}),
        }),
      });
    } catch (networkError) {
      throw new SuggestionsAPIError(
        0,
        null,
        networkError instanceof Error
          ? networkError.message
          : "クラウドAPIへの接続に失敗しました",
      );
    }

    const responseText = await response.text();
    let parsed: unknown = null;
    try {
      parsed = responseText ? JSON.parse(responseText) : null;
    } catch {
      parsed = null;
    }

    if (!response.ok) {
      if (response.status === 401) {
        if (responseText.includes("Authentication is not configured")) {
          throw new SuggestionsAPIError(
            401,
            null,
            "サーバー認証設定エラー: バックエンドの環境変数を確認してください",
          );
        }
        notifyUnauthorized();
      }
      const body =
        parsed && typeof parsed === "object"
          ? (parsed as SuggestionsErrorResponse)
          : null;
      throw new SuggestionsAPIError(
        response.status,
        body,
        `API Error: ${response.status}${responseText ? ` - ${responseText.slice(0, 200)}` : ""}`,
      );
    }

    if (!parsed || typeof parsed !== "object") {
      throw new SuggestionsAPIError(
        response.status,
        null,
        "Invalid JSON response from /suggestions",
      );
    }
    return parsed as SuggestionsResponse;
  },
};