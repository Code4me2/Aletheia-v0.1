'use client';

import { signIn, getSession } from 'next-auth/react';
import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useSidebarStore } from '@/store/sidebar';
import DarkModeWrapper from '@/components/DarkModeWrapper';
import { createLogger } from '@/utils/logger';

const logger = createLogger('signin-page');

function SignInContent() {
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get('callbackUrl') || '/chat';
  const urlError = searchParams.get('error');
  const { isDarkMode } = useSidebarStore();

  useEffect(() => {
    const checkSession = async () => {
      const session = await getSession();
      if (session) {
        // Ensure absolute path to prevent double /chat
        const absoluteUrl = callbackUrl.startsWith('/') ? callbackUrl : `/${callbackUrl}`;
        window.location.href = absoluteUrl;
      }
    };
    checkSession();
  }, [callbackUrl, router]);

  const handleCredentialsSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    // Validate email domain
    if (!email.endsWith('@reichmanjorgensen.com')) {
      setError('Only Reichman Jorgensen firm employees can sign in. Please use your @reichmanjorgensen.com email address.');
      setIsLoading(false);
      return;
    }

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
        callbackUrl
      });

      if (result?.error) {
        setError(result.error === 'CredentialsSignin' ? 'Invalid email or password' : result.error);
        setIsLoading(false);
      } else if (result?.ok) {
        // Ensure absolute path to prevent double /chat
        const absoluteUrl = callbackUrl.startsWith('/') ? callbackUrl : `/${callbackUrl}`;
        window.location.href = absoluteUrl;
      }
    } catch (error) {
      logger.error('Sign in error', error);
      setError('An unexpected error occurred. Please try again.');
      setIsLoading(false);
    }
  };

  const getErrorMessage = (error: string) => {
    switch (error) {
      case 'CredentialsSignin':
        return 'Invalid email or password. Please check your details and try again.';
      case 'SessionRequired':
        return 'Please sign in to access this page.';
      default:
        return 'An error occurred. Please try again.';
    }
  };

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
            <h1 className="text-4xl font-bold" style={{ color: isDarkMode ? '#ffffff' : '#004A84' }}>Aletheia-v0.1</h1>
          </div>

          {/* Sign In Card */}
          <div className={`${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} rounded-lg border p-10`}>
            <h2 className={`text-2xl font-semibold text-center mb-6 ${isDarkMode ? 'text-gray-100' : 'text-gray-900'}`}>
              Sign In
            </h2>

            {/* Error Message */}
            {(error || urlError) && (
              <div className={`mb-6 p-4 rounded-lg ${
                isDarkMode 
                  ? 'bg-red-900/20 border border-red-800' 
                  : 'bg-red-50 border border-red-200'
              }`}>
                <p className={`text-sm text-center ${
                  isDarkMode ? 'text-red-400' : 'text-red-600'
                }`}>
                  {error || (urlError ? getErrorMessage(urlError) : '')}
                </p>
              </div>
            )}

            {/* Email/Password Form */}
            <form onSubmit={handleCredentialsSignIn} className="space-y-4">
              <div>
                <label htmlFor="email" className={`block text-sm font-medium mb-2 ${
                  isDarkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="jsmith@reichmanjorgensen.com"
                  required
                  autoComplete="email"
                  className={`w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    isDarkMode 
                      ? 'bg-[#1a1b1e] border border-gray-600 text-gray-100 placeholder-gray-400' 
                      : 'border border-gray-300 text-gray-900 placeholder-gray-600'
                  }`}
                  disabled={isLoading}
                />
              </div>
              <div>
                <label htmlFor="password" className={`block text-sm font-medium mb-2 ${
                  isDarkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                  className={`w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    isDarkMode 
                      ? 'bg-[#1a1b1e] border border-gray-600 text-gray-100 placeholder-gray-400' 
                      : 'border border-gray-300 text-gray-900 placeholder-gray-600'
                  }`}
                  disabled={isLoading}
                />
              </div>
              <div className="flex justify-center pt-4">
                <button
                  type="submit"
                  disabled={isLoading}
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
                  {isLoading ? 'Signing in...' : 'Sign In'}
                </button>
              </div>
            </form>

            {/* Forgot Password Link */}
            <div className="mt-4 text-center">
              <Link
                href="/auth/forgot-password"
                className={`text-sm font-medium ${
                  isDarkMode ? 'text-[#C7A562] hover:text-[#B59552]' : 'text-[#004A84] hover:text-[#003A6C]'
                }`}
              >
                Forgot your password?
              </Link>
            </div>

            {/* Create Account Link */}
            <div className="mt-6 text-center">
              <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Don&apos;t have an account?{' '}
                <Link
                  href="/auth/register"
                  className={`font-medium ${
                    isDarkMode ? 'text-[#C7A562] hover:text-[#B59552]' : 'text-[#004A84] hover:text-[#003A6C]'
                  }`}
                >
                  Create Account
                </Link>
              </p>
            </div>
          </div>

        </div>
      </div>
    </>
  );
}

export default function SignIn() {
  const { isDarkMode } = useSidebarStore();
  
  return (
    <>
      <DarkModeWrapper><></></DarkModeWrapper>
      <Suspense fallback={
        <div className={`min-h-screen ${isDarkMode ? 'bg-[#1a1b1e]' : 'bg-gray-50'} flex items-center justify-center`}>
          <div className={`w-8 h-8 border-2 ${isDarkMode ? 'border-gray-400' : 'border-blue-600'} border-t-transparent rounded-full animate-spin`}></div>
        </div>
      }>
        <SignInContent />
      </Suspense>
    </>
  );
}