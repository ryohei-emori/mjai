// API configuration 
// All data access is via the backend REST API
// No direct database client usage in frontend for security


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
  
  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    
    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', response.status, errorText);
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
    isSelected: number;
    isModified: number;
    isCustom?: number;
    selectedOrder?: number;
  }) => {
    return await apiFetch('/proposals', {
      method: 'POST',
      body: JSON.stringify(proposalData)
    });
  }
};

// AI提案生成API（既存）
export const suggestionsAPI = {
  generateSuggestions: async (requestData: {
    originalText: string;
    targetText: string;
    instructionPrompt?: string;
    sessionId?: string;
    engine?: string;
  }) => {
    return await apiFetch('/suggestions', {
      method: 'POST',
      body: JSON.stringify(requestData)
    });
  }
}; 