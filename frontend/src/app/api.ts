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

// 履歴関連API
export const historyAPI = {
  // セッションの履歴一覧取得
  getHistories: async (sessionId: string) => {
    return await apiFetch(`/sessions/${sessionId}/histories`);
  },

  // 履歴作成
  createHistory: async (historyData: {
    sessionId: string;
    originalText: string;
    targetText: string;
    instructionPrompt?: string;
    combinedComment?: string;
    selectedProposalIds?: string;
    customProposals?: string;
  }) => {
    return await apiFetch('/histories', {
      method: 'POST',
      body: JSON.stringify(historyData)
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
  }
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
};

export type SuggestionsErrorResponse = {
  error: string;
  fallback_available: boolean;
  message?: string;
  groq_error?: string;
  cf_error?: string;
  /** True when cloud providers failed due to rate-limit / quota / cooldown. */
  rate_limited?: boolean;
  /** Loaded credential counts (no secrets) for ops diagnosis. */
  groq_pool_size?: number;
  cf_pool_size?: number;
};

/** Structured cloud-suggestions failure (quota/rate-limit visible to UI). */
export class SuggestionsAPIError extends Error {
  status: number;
  rateLimited: boolean;
  body: SuggestionsErrorResponse | null;

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
    const haystack = [
      body?.message,
      body?.error,
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
  generate: async (originalText: string, targetText: string): Promise<SuggestionsResponse> => {
    const fullUrl = `${API_BASE_URL}/suggestions`;
    const { data: { session } } = await supabase.auth.getSession();
    const authHeaders: Record<string, string> = session?.access_token
      ? { Authorization: `Bearer ${session.access_token}` }
      : {};

    let response: Response;
    try {
      response = await fetch(fullUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders,
        },
        body: JSON.stringify({ originalText, targetText }),
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