'use client'

import React from 'react'

interface BestPracticesModalProps {
  isOpen: boolean
  onClose: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
}

export default function BestPracticesModal({ isOpen, onClose, onKeyDown }: BestPracticesModalProps) {
  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="practices-title"
      onKeyDown={onKeyDown}
    >
      <div 
        className="glass rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden transform transition-all duration-300 scale-100 opacity-100"
        style={{ animation: 'modalEnter 0.3s ease-out' }}
        onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 glass border-b border-white/10 p-8">
          <h2 id="practices-title" className="text-3xl font-bold text-gradient">AI Best Practices</h2>
          <button
            onClick={onClose}
            aria-label="Close Best Practices modal"
            className="absolute top-8 right-8 text-gray-400 hover:text-white active:text-white transition-colors duration-200 group p-2 -m-2 rounded-lg hover:bg-white/10 active:bg-white/20"
          >
            <svg className="w-8 h-8 group-hover:rotate-90 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="p-8 space-y-6 overflow-y-auto max-h-[calc(85vh-100px)]">
          <section>
            <h3 className="text-2xl font-semibold mb-4 text-accent-royal-blue">Effective Prompting</h3>
            <ul className="space-y-3 text-gray-300">
              <li className="flex items-start gap-3">
                <span className="text-accent-denim-blue mt-1">•</span>
                Be clear and specific about your desired outcome
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-denim-blue mt-1">•</span>
                Provide relevant context and background information
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-denim-blue mt-1">•</span>
                Break complex tasks into smaller, manageable steps
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-denim-blue mt-1">•</span>
                Ask for explanations when needed for better understanding
              </li>
            </ul>
          </section>

          <section>
            <h3 className="text-2xl font-semibold mb-4 text-accent-gold">Quality Assurance</h3>
            <ul className="space-y-3 text-gray-300">
              <li className="flex items-start gap-3">
                <span className="text-accent-soft-gold mt-1">•</span>
                Always review and verify AI-generated content
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-soft-gold mt-1">•</span>
                Cross-reference important information with trusted sources
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-soft-gold mt-1">•</span>
                Use AI as a starting point, not the final product
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-soft-gold mt-1">•</span>
                Maintain critical thinking and professional judgment
              </li>
            </ul>
          </section>

          <section>
            <h3 className="text-2xl font-semibold mb-4 text-accent-denim-blue">Common Use Cases</h3>
            <div className="grid gap-4">
              <div className="glass rounded-lg p-4">
                <h4 className="font-semibold text-white mb-2">Research & Analysis</h4>
                <p className="text-sm text-gray-400">Gather information, summarize documents, and identify key points</p>
              </div>
              <div className="glass rounded-lg p-4">
                <h4 className="font-semibold text-white mb-2">Document Drafting</h4>
                <p className="text-sm text-gray-400">Create templates, outlines, and initial drafts for review</p>
              </div>
              <div className="glass rounded-lg p-4">
                <h4 className="font-semibold text-white mb-2">Communication</h4>
                <p className="text-sm text-gray-400">Improve clarity, tone, and structure of written communications</p>
              </div>
              <div className="glass rounded-lg p-4">
                <h4 className="font-semibold text-white mb-2">Learning & Development</h4>
                <p className="text-sm text-gray-400">Explore new topics and stay updated on industry trends</p>
              </div>
            </div>
          </section>

          <section className="glass rounded-xl p-6 border border-accent-soft-gold/30">
            <h3 className="text-xl font-semibold mb-3 text-accent-gold">Remember</h3>
            <p className="text-gray-300">
              AI is a powerful tool to enhance your capabilities, not replace your expertise. 
              Use it wisely to amplify your professional effectiveness while maintaining 
              the high standards of quality and ethics that define our firm.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}