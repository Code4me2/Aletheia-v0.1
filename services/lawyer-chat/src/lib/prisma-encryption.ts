/**
 * Prisma middleware for automatic field-level encryption
 */
import { encrypt, decrypt, shouldEncryptField, needsEncryption } from './crypto';

/**
 * Encrypt fields in the data object based on the model
 */
function encryptFields(model: string, data: any): any {
  if (!data || typeof data !== 'object') return data;
  
  const result = { ...data };
  
  for (const field in data) {
    if (shouldEncryptField(model, field) && data[field] !== null && data[field] !== undefined) {
      if (typeof data[field] === 'string' && needsEncryption(data[field])) {
        result[field] = encrypt(data[field]);
      }
    }
  }
  
  return result;
}

/**
 * Decrypt fields in the result object based on the model
 */
function decryptFields(model: string, data: any): any {
  if (!data || typeof data !== 'object') return data;
  
  if (Array.isArray(data)) {
    return data.map(item => decryptFields(model, item));
  }
  
  const result = { ...data };
  
  for (const field in data) {
    if (shouldEncryptField(model, field) && data[field] !== null && data[field] !== undefined) {
      try {
        result[field] = decrypt(data[field]);
      } catch (error) {
        console.warn(`Failed to decrypt ${model}.${field}, using original value`);
      }
    }
  }
  
  return result;
}

/**
 * Create encryption middleware for Prisma
 */
export function createEncryptionMiddleware() {
  return async (params: any, next: any) => {
    const writeOperations = ['create', 'update', 'updateMany', 'upsert'];
    const readOperations = ['findUnique', 'findUniqueOrThrow', 'findFirst', 'findFirstOrThrow', 'findMany'];
    
    // Encrypt data before write operations
    if (params.model && writeOperations.includes(params.action)) {
      if (params.args.data) {
        params.args.data = encryptFields(params.model, params.args.data);
      }
      if (params.args.create) {
        params.args.create = encryptFields(params.model, params.args.create);
      }
      if (params.args.update) {
        params.args.update = encryptFields(params.model, params.args.update);
      }
    }
    
    // Execute the query
    const result = await next(params);
    
    // Decrypt data after read operations
    if (params.model && readOperations.includes(params.action) && result) {
      return decryptFields(params.model, result);
    }
    
    return result;
  };
}