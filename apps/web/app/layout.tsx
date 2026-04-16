import type React from "react"
import type { Metadata } from "next"
import { Inter, JetBrains_Mono } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import "./globals.css"
import { SmoothScroll } from "@/components/providers/smooth-scroll"
import { TopNav } from "@/components/nav/top-nav"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
})

export const metadata: Metadata = {
  title: "ORACLE | AI-Driven Quantitative Trading Terminal",
  description:
    "The definitive AI-driven quantitative trading terminal. Neural ensemble predictions meet institutional-grade execution. Built on real market data. Verified by deflated Sharpe.",
  icons: {
    icon: [
      { url: "/icon-dark-32x32.png", media: "(prefers-color-scheme: dark)" },
      { url: "/icon.svg", type: "image/svg+xml" },
    ],
    apple: "/apple-icon.png",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased bg-background text-foreground`}
      >
        <SmoothScroll>
          <TopNav />
          {children}
        </SmoothScroll>
        <Analytics />
      </body>
    </html>
  )
}
