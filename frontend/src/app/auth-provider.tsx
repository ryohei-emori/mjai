"use client"

import { createContext, useContext, useEffect, useState, useCallback } from "react"
import type { Session, User } from "@supabase/supabase-js"
import { supabase } from "@/lib/supabaseClient"
import { registerUnauthorizedHandler } from "@/lib/authEvents"

type AuthContextValue = {
  session: Session | null
  user: User | null
  isLoading: boolean
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
  // apiFetch などが 401 を検知した際に強制的にログアウト状態へ遷移させるためのフック
  handleUnauthenticated: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

/**
 * OAuth リダイレクト後のハッシュフラグメントを検出
 * #access_token=... または #error=... があれば OAuth コールバック中と判定
 */
function detectOAuthCallback(): boolean {
  if (typeof window === "undefined") return false
  const hash = window.location.hash
  if (!hash || hash === "#") return false
  const hashParams = new URLSearchParams(hash.substring(1))
  return hashParams.has("access_token") || hashParams.has("error") || hashParams.has("error_description")
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isMounted = true
    let fallbackTimeoutId: ReturnType<typeof setTimeout> | null = null

    // OAuth コールバック中かどうかを判定
    const isOAuthCallback = detectOAuthCallback()

    if (isOAuthCallback) {
      // OAuth コールバック時: Supabase がハッシュトークンをパースして
      // onAuthStateChange を発火するのを待つ。getSession() は localStorage を
      // 参照するため、初回 OAuth 時は null を返す可能性がある。
      // フォールバックとして 5 秒後にタイムアウトさせる（何らかの理由でパースが失敗した場合）
      console.log("[auth] OAuth callback detected, waiting for hash token parsing...")
      fallbackTimeoutId = setTimeout(() => {
        if (!isMounted) return
        console.warn("[auth] OAuth hash parsing timeout, falling back to getSession()")
        supabase.auth.getSession().then(({ data }) => {
          if (!isMounted) return
          setSession(data.session)
          setIsLoading(false)
        })
      }, 5000)
    } else {
      // 通常のページロード: 永続化されたセッションを復元
      supabase.auth.getSession().then(({ data }) => {
        if (!isMounted) return
        setSession(data.session)
        setIsLoading(false)
      })
    }

    const { data: authListener } = supabase.auth.onAuthStateChange((event, newSession) => {
      if (!isMounted) return
      console.log("[auth] Auth state change:", event)
      // OAuth コールバックのタイムアウトをクリア
      if (fallbackTimeoutId) {
        clearTimeout(fallbackTimeoutId)
        fallbackTimeoutId = null
      }
      setSession(newSession)
      setIsLoading(false)
    })

    return () => {
      isMounted = false
      if (fallbackTimeoutId) {
        clearTimeout(fallbackTimeoutId)
      }
      authListener.subscription.unsubscribe()
    }
  }, [])

  const signInWithGoogle = useCallback(async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: typeof window !== "undefined" ? window.location.origin : undefined,
      },
    })
  }, [])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
    setSession(null)
  }, [])

  // バックエンドが401を返した場合（トークン失効・不正）にログイン画面へ戻す
  const handleUnauthenticated = useCallback(() => {
    setSession(null)
    supabase.auth.signOut()
  }, [])

  // apiFetch (api.ts) は React コンテキストを持たないため、モジュール間の
  // イベントブリッジ経由で 401 発生時にログアウト状態へ遷移させる
  useEffect(() => {
    return registerUnauthorizedHandler(handleUnauthenticated)
  }, [handleUnauthenticated])

  const value: AuthContextValue = {
    session,
    user: session?.user ?? null,
    isLoading,
    signInWithGoogle,
    signOut,
    handleUnauthenticated,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
