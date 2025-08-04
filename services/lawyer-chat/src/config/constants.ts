/**
 * Centralized configuration constants for the lawyer-chat application
 * This file serves as the single source of truth for all configuration values
 */

// API Configuration
export const API = {
  VERSION: 'v1',
  TIMEOUT_MS: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  MAX_RESPONSE_SIZE_BYTES: 30000, // 30KB max response size
} as const;

// Security Configuration
export const SECURITY = {
  ENCRYPTION: {
    ALGORITHM: 'aes-256-gcm' as const,
    IV_LENGTH: 16,
    KEY_ITERATIONS: 100000,
    SALT_LENGTH: 32,
    TAG_LENGTH: 16,
  },
  RATE_LIMIT: {
    WINDOW_MS: 60 * 1000, // 1 minute
    MAX_REQUESTS: 100,
    EDGE_WINDOW_MS: 60 * 1000, // 1 minute for edge rate limiting
    EDGE_MAX_REQUESTS: 10,
  },
  PASSWORD: {
    MIN_LENGTH: 8,
    BCRYPT_ROUNDS: 10,
  },
  SESSION: {
    MAX_AGE_SECONDS: 30 * 24 * 60 * 60, // 30 days
  },
} as const;

// Streaming Configuration
export const STREAM = {
  CHUNK_SIZE_CHARS: 2, // 2 characters per stream chunk
  CHUNK_DELAY_MS: 30, // 30ms delay between chunks for smooth streaming
  BUFFER_SIZE: 1024,
  ENCODER: 'utf-8' as const,
} as const;

// Chat Configuration
export const CHAT = {
  DEFAULT_TITLE: 'New Chat',
  MESSAGE_PREVIEW_LENGTH: 50, // Characters to show in preview
  WEBHOOK_TIMEOUT_MS: 30 * 1000, // 30 seconds
  STREAMING_UPDATE_INTERVAL_MS: 2000, // Update database every 2 seconds during streaming
} as const;

// Database Configuration
export const DATABASE = {
  PAGINATION: {
    DEFAULT_LIMIT: 20,
    MAX_LIMIT: 100,
  },
  RETRY: {
    MAX_ATTEMPTS: 3,
    DELAY_MS: 1000,
  },
} as const;

// Email Configuration
export const EMAIL = {
  VERIFICATION: {
    TOKEN_EXPIRY_HOURS: 24,
  },
  RESET_PASSWORD: {
    TOKEN_EXPIRY_HOURS: 1,
  },
} as const;

// File Size Limits
export const FILE_SIZE = {
  MAX_UPLOAD_BYTES: 10 * 1024 * 1024, // 10MB
  MAX_CHAT_EXPORT_BYTES: 50 * 1024 * 1024, // 50MB
} as const;

// UI Configuration
export const UI = {
  ANIMATION: {
    DURATION_MS: 300,
    LOADING_DELAY_MS: 200,
  },
  PAGINATION: {
    PAGE_SIZE: 10,
  },
} as const;