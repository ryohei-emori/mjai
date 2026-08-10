"use client"

import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react"
import type { Session, User, AuthChangeEvent } from "@supabase/supabase-js"
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
  // セッションが確立済みかどうかを追跡（API 401 処理用）
  const sessionEstablishedRef = useRef(false)

  useEffect(() => {
    let isMounted = true
    let fallbackTimeoutId: ReturnType<typeof setTimeout> | null = null

    // OAuth コールバック中かどうかを判定（useEffect 内で1回だけ評価）
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
          if (data.session) {
            sessionEstablishedRef.current = true
          }
          setIsLoading(false)
        })
      }, 5000)
    } else {
      // 通常のページロード: 永続化されたセッションを復元
      supabase.auth.getSession().then(({ data }) => {
        if (!isMounted) return
        setSession(data.session)
        if (data.session) {
          sessionEstablishedRef.current = true
        }
        setIsLoading(false)
      })
    }

    const { data: authListener } = supabase.auth.onAuthStateChange((event: AuthChangeEvent, newSession) => {
      if (!isMounted) return
      console.log("[auth] Auth state change:", event, newSession ? "with session" : "no session")

      // OAuth コールバック時の INITIAL_SESSION イベントで null セッションが来た場合は無視
      // Supabase はハッシュトークンをパースする前に INITIAL_SESSION を null で発火する
      if (isOAuthCallback && event === "INITIAL_SESSION" && !newSession) {
        console.log("[auth] Ignoring INITIAL_SESSION with null during OAuth callback")
        return
      }

      // OAuth コールバックのタイムアウトをクリア
      if (fallbackTimeoutId) {
        clearTimeout(fallbackTimeoutId)
        fallbackTimeoutId = null
      }

      setSession(newSession)
      if (newSession) {
        sessionEstablishedRef.current = true
      }
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
  // ただし、セッションが一度も確立されていない場合（OAuth フロー中）は即座にサインアウトしない
  const handleUnauthenticated = useCallback(() => {
    console.log("[auth] handleUnauthenticated called, sessionEstablished:", sessionEstablishedRef.current)
    
    // セッションが確立されていない場合は、まだOAuthフロー中の可能性があるため
    // 即座にサインアウトせず、現在のセッション状態を確認
    if (!sessionEstablishedRef.current) {
      console.log("[auth] Session not yet established, checking current session before sign out...")
      supabase.auth.getSession().then(({ data }) => {
        if (data.session) {
          // セッションがある場合は、トークンが有効かもしれないのでサインアウトしない
          console.log("[auth] Active session found, not signing out")
          setSession(data.session)
          sessionEstablishedRef.current = true
        } else {
          // セッションがない場合のみサインアウト
          console.log("[auth] No session found, clearing state")
          setSession(null)
        }
      })
      return
    }
    
    // セッションが確立済みの場合は、401 はトークン失効を意味するのでサインアウト
    console.log("[auth] Session was established, signing out due to 401")
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
