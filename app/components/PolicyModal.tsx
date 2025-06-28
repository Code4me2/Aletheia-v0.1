'use client'

import React from 'react'

interface PolicyModalProps {
  isOpen: boolean
  onClose: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
}

export default function PolicyModal({ isOpen, onClose, onKeyDown }: PolicyModalProps) {
  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="policy-title"
      onKeyDown={onKeyDown}
    >
      <div 
        className="glass rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden transform transition-all duration-300 scale-100 opacity-100"
        style={{ animation: 'modalEnter 0.3s ease-out' }}
        onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 glass border-b border-white/10 p-8">
          <h2 id="policy-title" className="text-3xl font-bold text-gradient">AI Security Protocols</h2>
          <button
            onClick={onClose}
            aria-label="Close AI Policy modal"
            className="absolute top-8 right-8 text-gray-400 hover:text-white active:text-white transition-colors duration-200 group p-2 -m-2 rounded-lg hover:bg-white/10 active:bg-white/20"
          >
            <svg className="w-8 h-8 group-hover:rotate-90 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="p-8 space-y-6 overflow-y-auto max-h-[calc(85vh-100px)]">
          <section>
            <h3 className="text-2xl font-semibold mb-4 text-accent-blue">Mission Statement</h3>
            <p className="text-gray-300 leading-relaxed">
              Our AI integration framework is designed to enhance legal excellence while maintaining 
              the highest standards of confidentiality, security, and professional ethics that define 
              our practice.
            </p>
          </section>

          <section>
            <h3 className="text-2xl font-semibold mb-4 text-accent-purple">Data Classification Matrix</h3>
            <div className="space-y-4">
              <div className="glass rounded-xl p-6 border border-green-500/30">
                <h4 className="font-semibold text-green-400 mb-3 flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Authorized Data Categories
                </h4>
                <ul className="text-sm text-gray-300 space-y-2">
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">▸</span>
                    Legal research queries and general case law analysis
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">▸</span>
                    Public domain documentation and regulatory frameworks
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">▸</span>
                    Template generation for standard legal documents
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">▸</span>
                    Procedural guidance and best practice frameworks
                  </li>
                </ul>
              </div>
              
              <div className="glass rounded-xl p-6 border border-red-500/30">
                <h4 className="font-semibold text-red-400 mb-3 flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                  </svg>
                  Restricted Information
                </h4>
                <ul className="text-sm text-gray-300 space-y-2">
                  <li className="flex items-start gap-2">
                    <span className="text-red-400 mt-1">▸</span>
                    Client-specific information and case details
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-red-400 mt-1">▸</span>
                    Internal strategic documents and privileged communications
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-red-400 mt-1">▸</span>
                    Financial data and billing information
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-red-400 mt-1">▸</span>
                    Personnel records and partnership agreements
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-2xl font-semibold mb-4 text-accent-gold">Implementation Guidelines</h3>
            <ul className="space-y-3 text-gray-300">
              <li className="flex items-start gap-3">
                <span className="text-accent-gold mt-1">1.</span>
                All AI interactions must be conducted through approved, encrypted channels
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-gold mt-1">2.</span>
                Regular audits will be conducted to ensure compliance with data protection standards
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-gold mt-1">3.</span>
                AI-generated content must be reviewed by qualified professionals before client delivery
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-gold mt-1">4.</span>
                Continuous training programs will ensure team proficiency with AI tools
              </li>
              <li className="flex items-start gap-3">
                <span className="text-accent-gold mt-1">5.</span>
                Incident response protocols are in place for any security concerns
              </li>
            </ul>
          </section>

          <section className="glass rounded-xl p-6 border border-accent-blue/30">
            <h3 className="text-xl font-semibold mb-3 text-accent-blue">Ready to Begin?</h3>
            <p className="text-gray-300 mb-4">
              Access our secure AI platform using your firm credentials. All sessions are monitored 
              and encrypted to ensure complete confidentiality.
            </p>
            <button
              onClick={onClose}
              className="px-6 py-3 bg-gradient-to-r from-accent-denim-blue to-accent-royal-blue rounded-lg text-white font-semibold hover:scale-105 transition-transform duration-200"
            >
              I Understand and Accept
            </button>
          </section>
        </div>
      </div>
    </div>
  )
}