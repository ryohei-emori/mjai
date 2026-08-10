import { createClient, SupabaseClient } from "@supabase/supabase-js"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ""
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""

// 環境変数が設定されているかどうか（空文字チェック）
const isConfigured = !!supabaseUrl && !!supabaseAnonKey

if (!isConfigured) {
  console.warn(
    "Supabase の環境変数が設定されていません（NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY）。ログイン機能は動作しません。"
  )
}

// ブラウザ用 Supabase クライアント。セッションは既定で localStorage に永続化され、
// トークンの自動リフレッシュも Supabase クライアントが内部で処理する。
// 
// Note: ビルド時（SSG/prerender）で環境変数が設定されていない場合、
// createClient はダミーURLで初期化される。この場合、実際の認証リクエストは失敗するが、
// ビルド自体は成功する。Vercel の本番環境では正しい環境変数が設定される。
export const supabase: SupabaseClient = createClient(
  supabaseUrl || "https://placeholder.supabase.co",
  supabaseAnonKey || "placeholder-anon-key",
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  }
)
