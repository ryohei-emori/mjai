import type { Metadata, Viewport } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "./auth-provider";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MJAI - 日本語添削アシスタント",
  description: "日本語テキスト添削支援アプリケーション",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // By default only the visual viewport shrinks when the on-screen keyboard
  // opens, so `dvh` keeps reporting the full height and the field being typed
  // into can end up behind the keyboard. `resizes-content` shrinks the layout
  // viewport too, which is what makes `.h-viewport` follow the keyboard.
  // Ignored where unsupported (pre-Chrome 108, Safari), leaving today's
  // behaviour.
  interactiveWidget: "resizes-content",
  // `maximumScale` and `userScalable` are deliberately absent: suppressing
  // pinch zoom is the usual collateral damage of a mobile pass and this app
  // shows dense CJK text that people need to be able to magnify.
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // suppressHydrationWarning: browser extensions (e.g. UI.Vision/Kantu) inject attrs like data-kantu on <html>
  return (
    <html lang="ja" suppressHydrationWarning>
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className={`bg-background text-foreground font-sans ${inter.variable} ${geistMono.variable}`}>
        <AuthProvider>
          <Toaster />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
