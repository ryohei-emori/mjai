"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FileText, Loader2 } from "lucide-react"
import { useAuth } from "./auth-provider"

export function LoginScreen() {
  const { signInWithGoogle } = useAuth()
  const [isSigningIn, setIsSigningIn] = useState(false)

  const handleSignIn = async () => {
    setIsSigningIn(true)
    try {
      await signInWithGoogle()
    } finally {
      setIsSigningIn(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="max-w-md w-full">
        <CardHeader className="text-center">
          <FileText className="w-12 h-12 mx-auto mb-4 text-blue-600" />
          <CardTitle>CCTalk 添削システム</CardTitle>
          <CardDescription>続けるにはGoogleアカウントでログインしてください</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleSignIn} disabled={isSigningIn} className="w-full" size="lg">
            {isSigningIn ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                リダイレクト中...
              </>
            ) : (
              "Googleでログイン"
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
