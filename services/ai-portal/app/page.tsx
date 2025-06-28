'use client'

import { useState, useEffect, useCallback } from 'react'
import Image from 'next/image'
import PolicyModal from './components/PolicyModal'
import BestPracticesModal from './components/BestPracticesModal'

// Import the logo directly
import logoImage from '../public/rjlf_logo.png'

// Create a blur placeholder
const shimmer = (w: number, h: number) => `
<svg width="${w}" height="${h}" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <defs>
    <linearGradient id="g">
      <stop stop-color="#333" offset="20%" />
      <stop stop-color="#222" offset="50%" />
      <stop stop-color="#333" offset="70%" />
    </linearGradient>
  </defs>
  <rect width="${w}" height="${h}" fill="#333" />
  <rect id="r" width="${w}" height="${h}" fill="url(#g)" />
  <animate xlink:href="#r" attributeName="x" from="-${w}" to="${w}" dur="1s" repeatCount="indefinite"  />
</svg>`

const toBase64 = (str: string) =>
  typeof window === 'undefined'
    ? Buffer.from(str).toString('base64')
    : window.btoa(str)

const dataUrl = `data:image/svg+xml;base64,${toBase64(shimmer(600, 200))}`

export default function Home() {
  const [showPolicy, setShowPolicy] = useState(false)
  const [showBestPractices, setShowBestPractices] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Keyboard event handlers
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowPolicy(false)
        setShowBestPractices(false)
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [])

  // Focus trap for modals
  const handleModalKeyDown = useCallback((e: React.KeyboardEvent, closeModal: () => void) => {
    if (e.key === 'Escape') {
      closeModal()
    }
  }, [])

  return (
    <main className="min-h-screen bg-dark-900 flex flex-col overflow-hidden relative">
      {/* Dynamic Background */}
      <div className="fixed inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-conic from-accent-royal-blue/20 via-transparent to-accent-denim-blue/20 blur-3xl animate-spin-slow" />
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-conic from-accent-soft-gold/20 via-transparent to-accent-gold/20 blur-3xl animate-spin-slow" style={{ animationDirection: 'reverse', animationDuration: '20s' }} />
        <div className="absolute inset-0 bg-dark-900/80" />
      </div>

      {/* Grid Pattern Overlay */}
      <div className="fixed inset-0 opacity-50" style={{ backgroundImage: "url('data:image/svg+xml,%3Csvg width=\"100\" height=\"100\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cdefs%3E%3Cpattern id=\"grid\" width=\"100\" height=\"100\" patternUnits=\"userSpaceOnUse\"%3E%3Cpath d=\"M 100 0 L 0 0 0 100\" fill=\"none\" stroke=\"rgba(255,255,255,0.02)\" stroke-width=\"1\"/%3E%3C/pattern%3E%3C/defs%3E%3Crect width=\"100%25\" height=\"100%25\" fill=\"url(%23grid)\" /%3E%3C/svg%3E')" }} />

      <header className={`relative z-10 flex justify-center p-8 transition-all duration-1000 ${mounted ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0'}`}>
        <div className="glass-logo rounded-2xl px-8 py-4 animate-glow-logo">
          <Image
            src={logoImage}
            alt="Reichman Jorgensen Lehman & Feldberg LLP"
            width={600}
            height={200}
            className="h-20 md:h-28 w-auto"
            priority
            placeholder="blur"
            blurDataURL={dataUrl}
            quality={100}
          />
        </div>
      </header>
      
      <div className="flex-1 flex items-center justify-center px-4 relative z-10">
        <div className="text-center max-w-5xl relative">
          {/* Floating Particles */}
          <div className="absolute inset-0 -z-10">
            <div className="absolute top-0 left-1/4 w-2 h-2 bg-accent-royal-blue rounded-full animate-float blur-sm" style={{ animationDelay: '0s' }} />
            <div className="absolute bottom-1/4 right-1/3 w-3 h-3 bg-accent-denim-blue rounded-full animate-float blur-sm" style={{ animationDelay: '2s' }} />
            <div className="absolute top-1/3 right-1/4 w-2 h-2 bg-accent-soft-gold rounded-full animate-float blur-sm" style={{ animationDelay: '4s' }} />
          </div>

          <h1 className={`text-5xl md:text-7xl font-bold mb-16 transition-all duration-1000 delay-300 ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
            <span className="text-gradient">RJLF AI Portal</span>
          </h1>
          
          <div className="flex flex-col lg:flex-row gap-6 justify-center items-center max-w-5xl mx-auto">
            <button
              onClick={() => setShowPolicy(true)}
              aria-label="View AI Security Policy"
              aria-haspopup="dialog"
              className={`group relative px-8 py-5 overflow-hidden rounded-xl transition-all duration-500 transform w-full lg:w-auto lg:min-w-[200px] hover:scale-105 active:scale-100 ${mounted ? 'translate-y-0 opacity-100 scale-100' : 'translate-y-10 opacity-0 scale-95'}`}
              style={{ transitionDelay: '700ms' }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-rjlf-blue via-accent-royal-blue to-white opacity-90 group-hover:opacity-100 transition-all duration-700 ease-in-out" />
              <div className="absolute inset-0 bg-gradient-to-r from-white via-accent-royal-blue to-rjlf-blue opacity-0 group-hover:opacity-90 transition-all duration-700 ease-in-out" />
              <span className="relative flex items-center justify-center gap-3 text-white font-semibold text-lg">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                AI Policy
              </span>
              <div className="absolute inset-0 border-2 border-white/20 rounded-xl group-hover:scale-105 transition-transform duration-300" />
            </button>
            
            <button
              onClick={() => setShowBestPractices(true)}
              aria-label="View AI Best Practices"
              aria-haspopup="dialog"
              className={`group relative px-8 py-5 overflow-hidden rounded-xl transition-all duration-500 transform w-full lg:w-auto lg:min-w-[200px] hover:scale-105 active:scale-100 ${mounted ? 'translate-y-0 opacity-100 scale-100' : 'translate-y-10 opacity-0 scale-95'}`}
              style={{ transitionDelay: '900ms' }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-accent-soft-gold via-accent-gold to-white opacity-90 group-hover:opacity-100 transition-all duration-700 ease-in-out" />
              <div className="absolute inset-0 bg-gradient-to-r from-white via-accent-gold to-accent-soft-gold opacity-0 group-hover:opacity-90 transition-all duration-700 ease-in-out" />
              <span className="relative flex items-center justify-center gap-3 text-white font-semibold text-lg">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Best Practices
              </span>
              <div className="absolute inset-0 border-2 border-white/20 rounded-xl group-hover:scale-105 transition-transform duration-300" />
            </button>
            
            <a
              href="https://claude.ai"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open Claude AI in a new tab"
              className={`group relative px-8 py-5 overflow-hidden rounded-xl transition-all duration-500 transform w-full lg:w-auto lg:min-w-[200px] hover:scale-105 active:scale-100 ${mounted ? 'translate-y-0 opacity-100 scale-100' : 'translate-y-10 opacity-0 scale-95'}`}
              style={{ transitionDelay: '1100ms' }}
            >
              <div className="absolute inset-0 glass" />
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
              <span className="relative flex items-center justify-center gap-3 text-white font-semibold text-lg">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M17.5 3C19.433 3 21 4.567 21 6.5V17.5C21 19.433 19.433 21 17.5 21H6.5C4.567 21 3 19.433 3 17.5V6.5C3 4.567 4.567 3 6.5 3H17.5ZM17.5 4.5H6.5C5.396 4.5 4.5 5.396 4.5 6.5V17.5C4.5 18.604 5.396 19.5 6.5 19.5H17.5C18.604 19.5 19.5 18.604 19.5 17.5V6.5C19.5 5.396 18.604 4.5 17.5 4.5ZM15.178 8.75L12 15.5L8.822 8.75H10.5L12 11.75L13.5 8.75H15.178Z"/>
                </svg>
                Claude
              </span>
              <div className="absolute inset-0 border border-accent-soft-gold/50 rounded-xl group-hover:border-accent-gold transition-colors duration-300" />
            </a>
            
            <a
              href="http://localhost:8080/chat"
              aria-label="Open Aletheia chat"
              className={`group relative px-8 py-5 overflow-hidden rounded-xl transition-all duration-500 transform w-full lg:w-auto lg:min-w-[200px] hover:scale-105 active:scale-100 ${mounted ? 'translate-y-0 opacity-100 scale-100' : 'translate-y-10 opacity-0 scale-95'}`}
              style={{ transitionDelay: '1300ms' }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-gray-500 via-gray-600 to-gray-700 opacity-90 group-hover:opacity-100 transition-all duration-700 ease-in-out" />
              <div className="absolute inset-0 bg-gradient-to-r from-gray-700 via-gray-600 to-gray-500 opacity-0 group-hover:opacity-90 transition-all duration-700 ease-in-out" />
              <span className="relative flex items-center justify-center gap-3 text-white font-semibold text-lg">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                Aletheia-v0.1
              </span>
              <div className="absolute inset-0 border-2 border-white/20 rounded-xl group-hover:scale-105 transition-transform duration-300" />
            </a>
          </div>
        </div>
      </div>

      <PolicyModal 
        isOpen={showPolicy}
        onClose={() => setShowPolicy(false)}
        onKeyDown={(e) => handleModalKeyDown(e, () => setShowPolicy(false))}
      />

      <BestPracticesModal
        isOpen={showBestPractices}
        onClose={() => setShowBestPractices(false)}
        onKeyDown={(e) => handleModalKeyDown(e, () => setShowBestPractices(false))}
      />
    </main>
  )
}