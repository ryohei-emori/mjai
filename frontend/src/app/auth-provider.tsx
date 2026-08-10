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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isMounted = true

    // 永続化されたセッションを復元（ページリロード・新規タブ対応）
    supabase.auth.getSession().then(({ data }) => {
      if (!isMounted) return
      setSession(data.session)
      setIsLoading(false)
    })

    const { data: authListener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      if (!isMounted) return
      setSession(newSession)
      setIsLoading(false)
    })

    return () => {
      isMounted = false
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
