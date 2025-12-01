import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Enterprise DNA Cockpit',
  description: 'Management interface for Enterprise DNA platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

