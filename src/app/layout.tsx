import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Aetheris HR AI Copilot - Premium HR Assistant',
  description: 'Enterprise AI Assistant for HR Operations using Model Context Protocol (MCP).',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="light" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap" rel="stylesheet" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#2563eb" />
      </head>
      <body className="bg-slate-50 text-slate-900 min-h-screen flex flex-col font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} suppressHydrationWarning>
        {children}
      </body>
    </html>
  )
}
