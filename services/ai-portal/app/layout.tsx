import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ErrorBoundary from './components/ErrorBoundary'

const inter = Inter({ subsets: ['latin'] })

const basePath = process.env.NODE_ENV === 'production' && process.env.GITHUB_PAGES === 'true' 
  ? '/landing_page_RJLF' 
  : ''

export const metadata: Metadata = {
  title: 'RJLF AI Portal',
  description: 'Reichman Jorgensen Lehman & Feldberg LLP AI Integration Portal',
  icons: {
    icon: `${basePath}/rjlf_logo.png`,
  },
  other: {
    'link rel="preload" as="image" href': `${basePath}/rjlf_logo.png`,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
      </body>
    </html>
  )
}