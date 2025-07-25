'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useSidebarStore } from '@/store/sidebar';
import DarkModeWrapper from '@/components/DarkModeWrapper';
import { Eye, EyeOff, Check, X } from 'lucide-react';
import { api } from '@/utils/api';
import { createLogger } from '@/utils/logger';

const logger = createLogger('register-page');

export default function Register() {
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [emailSent, setEmailSent] = useState(true);
  const { isDarkMode } = useSidebarStore();

  // Password validation rules
  const passwordRules = [
    { test: (p: string) => p.length >= 8, text: 'At least 8 characters' },
    { test: (p: string) => /[A-Z]/.test(p), text: 'One uppercase letter' },
    { test: (p: string) => /[a-z]/.test(p), text: 'One lowercase letter' },
    { test: (p: string) => /\d/.test(p), text: 'One number' },
    { test: (p: string) => /[@$!%*?&]/.test(p), text: 'One special character' }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await api.post('/api/auth/register', formData);

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || 'Registration failed');
        setIsLoading(false);
        return;
      }

      // Check if email was sent successfully
      if (data.emailSent === false) {
        setEmailSent(false);
      }
      
      setSuccess(true);
    } catch (error) {
      logger.error('Registration error', error);
      setError('An unexpected error occurred. Please try again.');
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <>
        <DarkModeWrapper><></></DarkModeWrapper>
        <div className={`min-h-screen ${isDarkMode ? 'bg-[#1a1b1e]' : 'bg-gray-50'} flex items-center justify-center p-4`}>
          <div className="max-w-lg w-full">
            <div className={`${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} rounded-lg border p-10 text-center`}>
              <div className="mb-6">
                <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center ${
                  isDarkMode ? 'bg-green-900/20' : 'bg-green-100'
                }`}>
                  <Check size={32} className={isDarkMode ? 'text-green-400' : 'text-green-600'} />
                </div>
              </div>
              
              <h2 className={`text-2xl font-semibold mb-4 ${isDarkMode ? 'text-gray-100' : 'text-gray-900'}`}>
                {emailSent ? 'Check Your Email' : 'Registration Successful'}
              </h2>
              
              {emailSent ? (
                <>
                  <p className={`mb-6 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    We&apos;ve sent a verification link to <strong>{formData.email}</strong>
                  </p>
                  
                  <p className={`text-sm mb-6 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Please check your email and click the verification link to activate your account. 
                    The link will expire in 24 hours.
                  </p>
                  
                  <div className={`p-4 rounded-lg ${
                    isDarkMode ? 'bg-[#1a1b1e] border border-gray-700' : 'bg-gray-50 border border-gray-200'
                  }`}>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Didn&apos;t receive the email? Check your spam folder or contact IT support.
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <p className={`mb-6 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    Your account has been created successfully for <strong>{formData.email}</strong>
                  </p>
                  
                  <div className={`p-4 mb-6 rounded-lg ${
                    isDarkMode ? 'bg-yellow-900/20 border border-yellow-800' : 'bg-yellow-50 border border-yellow-200'
                  }`}>
                    <p className={`text-sm ${isDarkMode ? 'text-yellow-300' : 'text-yellow-800'} font-medium mb-2`}>
                      Email Verification Pending
                    </p>
                    <p className={`text-sm ${isDarkMode ? 'text-yellow-400' : 'text-yellow-700'}`}>
                      We had trouble sending the verification email. You can request a new verification email from the sign in page.
                    </p>
                  </div>
                  
                  <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    You&apos;ll need to verify your email address before you can sign in. 
                    Visit the sign in page to request a new verification email.
                  </p>
                </>
              )}
              
              <Link
                href="/auth/signin"
                className={`inline-block mt-6 text-sm font-medium ${
                  isDarkMode ? 'text-[#C7A562] hover:text-[#B59552]' : 'text-[#004A84] hover:text-[#003A6C]'
                }`}
              >
                Return to Sign In
              </Link>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <DarkModeWrapper><></></DarkModeWrapper>
      <div className={`min-h-screen ${isDarkMode ? 'bg-[#1a1b1e]' : 'bg-gray-50'} flex items-center justify-center p-4`}>
        <div className="max-w-lg w-full">
          {/* Logo and Header */}
          <div className="text-center mb-10">
            <img 
              src="/chat/logo.png" 
              alt="AI Legal Logo" 
              className="mx-auto mb-4 h-20 w-20 object-contain"
            />
            <h1 className="text-4xl font-bold" style={{ color: isDarkMode ? '#ffffff' : '#004A84' }}>AI Legal</h1>
          </div>

          {/* Registration Card */}
          <div className={`${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} rounded-lg border p-10`}>
            <h2 className={`text-2xl font-semibold text-center mb-6 ${isDarkMode ? 'text-gray-100' : 'text-gray-900'}`}>
              Create Account
            </h2>

            {/* Error Message */}
            {error && (
              <div className={`mb-6 p-4 rounded-lg ${
                isDarkMode 
                  ? 'bg-red-900/20 border border-red-800' 
                  : 'bg-red-50 border border-red-200'
              }`}>
                <p className={`text-sm text-center ${isDarkMode ? 'text-red-400' : 'text-red-600'}`}>
                  {error}
                </p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name Field */}
              <div>
                <label htmlFor="name" className={`block text-sm font-medium mb-2 ${
                  isDarkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Full Name
                </label>
                <input
                  id="name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="John Smith"
                  className={`w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    isDarkMode 
                      ? 'bg-[#1a1b1e] border border-gray-600 text-gray-100 placeholder-gray-400' 
                      : 'border border-gray-300 text-gray-900 placeholder-gray-600'
                  }`}
                  disabled={isLoading}
                />
              </div>

              {/* Email Field */}
              <div>
                <label htmlFor="email" className={`block text-sm font-medium mb-2 ${
                  isDarkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="jsmith@reichmanjorgensen.com"
                  required
                  className={`w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    isDarkMode 
                      ? 'bg-[#1a1b1e] border border-gray-600 text-gray-100 placeholder-gray-400' 
                      : 'border border-gray-300 text-gray-900 placeholder-gray-600'
                  }`}
                  disabled={isLoading}
                />
                <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  Must be a @reichmanjorgensen.com email address
                </p>
              </div>

              {/* Password Field */}
              <div>
                <label htmlFor="password" className={`block text-sm font-medium mb-2 ${
                  isDarkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="Create a strong password"
                    required
                    className={`w-full px-4 py-3 pr-12 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      isDarkMode 
                        ? 'bg-[#1a1b1e] border border-gray-600 text-gray-100 placeholder-gray-400' 
                        : 'border border-gray-300 text-gray-900 placeholder-gray-600'
                    }`}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className={`absolute right-3 top-3.5 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>

                {/* Password Requirements */}
                {formData.password && (
                  <div className={`mt-2 p-3 rounded-lg ${
                    isDarkMode ? 'bg-[#1a1b1e] border border-gray-700' : 'bg-gray-50 border border-gray-200'
                  }`}>
                    <p className={`text-xs font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Password must contain:
                    </p>
                    <div className="space-y-1">
                      {passwordRules.map((rule, index) => (
                        <div key={index} className="flex items-center gap-2 text-xs">
                          {rule.test(formData.password) ? (
                            <Check size={14} className={isDarkMode ? 'text-green-400' : 'text-green-600'} />
                          ) : (
                            <X size={14} className={isDarkMode ? 'text-gray-500' : 'text-gray-400'} />
                          )}
                          <span className={
                            rule.test(formData.password)
                              ? isDarkMode ? 'text-green-400' : 'text-green-600'
                              : isDarkMode ? 'text-gray-400' : 'text-gray-500'
                          }>
                            {rule.text}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password Field */}
              <div>
                <label htmlFor="confirmPassword" className={`block text-sm font-medium mb-2 ${
                  isDarkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Confirm Password
                </label>
                <div className="relative">
                  <input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    placeholder="Re-enter your password"
                    required
                    className={`w-full px-4 py-3 pr-12 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      isDarkMode 
                        ? 'bg-[#1a1b1e] border border-gray-600 text-gray-100 placeholder-gray-400' 
                        : 'border border-gray-300 text-gray-900 placeholder-gray-600'
                    }`}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className={`absolute right-3 top-3.5 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}
                  >
                    {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
                {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                  <p className={`text-xs mt-1 ${isDarkMode ? 'text-red-400' : 'text-red-600'}`}>
                    Passwords do not match
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <div className="flex justify-center pt-4">
                <button
                  type="submit"
                  disabled={isLoading || !passwordRules.every(rule => rule.test(formData.password)) || formData.password !== formData.confirmPassword}
                  className="px-8 py-3 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                  style={{
                    backgroundColor: isDarkMode ? 'transparent' : '#C7A562',
                    border: isDarkMode ? '2px solid #d1d1d1' : 'none',
                    color: isDarkMode ? '#d1d1d1' : '#004A84'
                  }}
                  onMouseEnter={(e) => {
                    if (!isLoading) {
                      if (!isDarkMode) (e.target as HTMLButtonElement).style.backgroundColor = '#B59552';
                      else (e.target as HTMLButtonElement).style.backgroundColor = '#404147';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isLoading) {
                      if (!isDarkMode) (e.target as HTMLButtonElement).style.backgroundColor = '#C7A562';
                      else (e.target as HTMLButtonElement).style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  {isLoading ? 'Creating Account...' : 'Create Account'}
                </button>
              </div>
            </form>

            {/* Sign In Link */}
            <div className="mt-6 text-center">
              <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Already have an account?{' '}
                <Link
                  href="/auth/signin"
                  className={`font-medium ${
                    isDarkMode ? 'text-[#C7A562] hover:text-[#B59552]' : 'text-[#004A84] hover:text-[#003A6C]'
                  }`}
                >
                  Sign In
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}