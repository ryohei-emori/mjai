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
// Primary: Cloud LLM (Groq/Cloudflare) via backend
// Fallback: Client-side WebLLM (when API unavailable or offline mode)
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
};

export const suggestionsAPI = {
  // Generate AI suggestions via backend (Groq/Cloudflare)
  generate: async (originalText: string, targetText: string): Promise<SuggestionsResponse> => {
    const response = await apiFetch('/suggestions', {
      method: 'POST',
      body: JSON.stringify({ originalText, targetText })
    });
    return response as SuggestionsResponse;
  },
};