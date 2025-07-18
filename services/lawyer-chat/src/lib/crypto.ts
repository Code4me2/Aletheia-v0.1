/**
 * Field-level encryption utilities for sensitive data
 * Uses AES-256-GCM for authenticated encryption
 */
import * as crypto from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16; // 128 bits
const SALT_LENGTH = 32; // 256 bits
const TAG_LENGTH = 16; // 128 bits
const KEY_LENGTH = 32; // 256 bits
const ITERATIONS = 100000; // PBKDF2 iterations

// Prefix to identify encrypted values
const ENCRYPTION_PREFIX = 'enc:v1:';

/**
 * Get or derive encryption key from environment
 */
function getEncryptionKey(): Buffer {
  const masterKey = process.env.FIELD_ENCRYPTION_KEY || process.env.NEXTAUTH_SECRET;
  
  if (!masterKey) {
    throw new Error('FIELD_ENCRYPTION_KEY or NEXTAUTH_SECRET must be set for field encryption');
  }
  
  // Use a fixed salt for deterministic key derivation
  const salt = crypto.createHash('sha256').update('field-encryption-v1').digest();
  
  return crypto.pbkdf2Sync(masterKey, salt, ITERATIONS, KEY_LENGTH, 'sha256');
}

/**
 * Encrypt a string value
 */
export function encrypt(text: string | null | undefined): string | null {
  if (!text) return null;
  
  try {
    const key = getEncryptionKey();
    const iv = crypto.randomBytes(IV_LENGTH);
    const salt = crypto.randomBytes(SALT_LENGTH);
    
    // Derive a unique key for this encryption using the salt
    const derivedKey = crypto.pbkdf2Sync(key, salt, 1000, KEY_LENGTH, 'sha256');
    
    const cipher = crypto.createCipheriv(ALGORITHM, derivedKey, iv);
    
    const encrypted = Buffer.concat([
      cipher.update(text, 'utf8'),
      cipher.final()
    ]);
    
    const authTag = cipher.getAuthTag();
    
    // Combine salt, iv, authTag, and encrypted data
    const combined = Buffer.concat([salt, iv, authTag, encrypted]);
    
    // Add prefix to identify encrypted values
    return ENCRYPTION_PREFIX + combined.toString('base64');
  } catch (error) {
    console.error('Encryption error:', error);
    throw new Error('Failed to encrypt data');
  }
}

/**
 * Decrypt a string value
 */
export function decrypt(encryptedText: string | null | undefined): string | null {
  if (!encryptedText) return null;
  
  // Check if value is encrypted
  if (!encryptedText.startsWith(ENCRYPTION_PREFIX)) {
    return encryptedText; // Return as-is if not encrypted
  }
  
  try {
    const key = getEncryptionKey();
    const encryptedData = encryptedText.slice(ENCRYPTION_PREFIX.length);
    const combined = Buffer.from(encryptedData, 'base64');
    
    // Extract components
    const salt = combined.slice(0, SALT_LENGTH);
    const iv = combined.slice(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
    const authTag = combined.slice(SALT_LENGTH + IV_LENGTH, SALT_LENGTH + IV_LENGTH + TAG_LENGTH);
    const encrypted = combined.slice(SALT_LENGTH + IV_LENGTH + TAG_LENGTH);
    
    // Derive the key using the salt
    const derivedKey = crypto.pbkdf2Sync(key, salt, 1000, KEY_LENGTH, 'sha256');
    
    const decipher = crypto.createDecipheriv(ALGORITHM, derivedKey, iv);
    decipher.setAuthTag(authTag);
    
    const decrypted = Buffer.concat([
      decipher.update(encrypted),
      decipher.final()
    ]);
    
    return decrypted.toString('utf8');
  } catch (error) {
    console.error('Decryption error:', error);
    throw new Error('Failed to decrypt data');
  }
}

/**
 * Check if a value needs encryption
 */
export function needsEncryption(value: string | null | undefined): boolean {
  if (!value) return false;
  return !value.startsWith(ENCRYPTION_PREFIX);
}

/**
 * List of fields that should be encrypted
 */
export const ENCRYPTED_FIELDS = {
  User: ['registrationToken', 'passwordResetToken', 'registrationIp', 'lastLoginIp'],
  Session: ['sessionToken'],
  Account: ['refresh_token', 'access_token', 'id_token'],
  VerificationToken: ['token'],
  AuditLog: ['ipAddress']
} as const;

/**
 * Check if a field should be encrypted
 */
export function shouldEncryptField(model: string, field: string): boolean {
  const fields = ENCRYPTED_FIELDS[model as keyof typeof ENCRYPTED_FIELDS] as readonly string[] | undefined;
  return fields ? fields.includes(field) : false;
}