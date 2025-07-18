#!/usr/bin/env node

/**
 * Migration script to encrypt existing sensitive fields in the database
 * This should be run once after enabling field-level encryption
 */

import { PrismaClient } from '@prisma/client';
import { encrypt, needsEncryption, ENCRYPTED_FIELDS } from '../src/lib/crypto';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });
dotenv.config({ path: '.env' });

// Create a raw Prisma client without middleware
const prisma = new PrismaClient({
  log: ['warn', 'error']
});

async function reencryptModel(model: string, encryptedFields: readonly string[]) {
  console.log(`\n🔍 Processing ${model}...`);
  
  try {
    // Get all records
    const rows = await (prisma as any)[model].findMany();
    console.log(`   Found ${rows.length} ${model} records`);
    
    let encryptedCount = 0;
    
    for (const row of rows) {
      const updates: Record<string, any> = {};
      let needsUpdate = false;
      
      for (const field of encryptedFields) {
        const value = row[field];
        if (typeof value === 'string' && value.length > 0 && needsEncryption(value)) {
          try {
            updates[field] = encrypt(value);
            needsUpdate = true;
          } catch (error) {
            console.error(`   ❌ Failed to encrypt ${model}.${field} for record ${row.id}:`, error);
          }
        }
      }
      
      if (needsUpdate) {
        try {
          await (prisma as any)[model].update({
            where: { id: row.id },
            data: updates,
          });
          encryptedCount++;
          console.log(`   ✅ Encrypted fields in ${model} record ${row.id}`);
        } catch (error) {
          console.error(`   ❌ Failed to update ${model} record ${row.id}:`, error);
        }
      }
    }
    
    console.log(`   ✅ Encrypted ${encryptedCount} out of ${rows.length} ${model} records`);
    
  } catch (error) {
    console.error(`❌ Failed to process ${model}:`, error);
  }
}

async function main() {
  console.log('🔐 Field-Level Encryption Migration Script');
  console.log('=========================================');
  
  // Check if encryption key is set
  if (!process.env.FIELD_ENCRYPTION_KEY && !process.env.NEXTAUTH_SECRET) {
    console.error('❌ Error: FIELD_ENCRYPTION_KEY or NEXTAUTH_SECRET must be set');
    process.exit(1);
  }
  
  console.log('✅ Encryption key found');
  console.log('\nThis script will encrypt the following sensitive fields:');
  
  for (const [model, fields] of Object.entries(ENCRYPTED_FIELDS)) {
    console.log(`\n${model}:`);
    fields.forEach(field => console.log(`  - ${field}`));
  }
  
  console.log('\n⚠️  WARNING: This will modify your database. Make sure you have a backup!');
  console.log('Press Ctrl+C to cancel, or wait 5 seconds to continue...\n');
  
  await new Promise(resolve => setTimeout(resolve, 5000));
  
  console.log('Starting encryption...');
  
  // Process each model
  for (const [model, fields] of Object.entries(ENCRYPTED_FIELDS)) {
    await reencryptModel(model, fields);
  }
  
  console.log('\n✅ Migration completed!');
  console.log('\nNext steps:');
  console.log('1. Test your application to ensure everything works correctly');
  console.log('2. Monitor logs for any decryption errors');
  console.log('3. Keep your FIELD_ENCRYPTION_KEY secure and backed up');
}

main()
  .catch((err) => {
    console.error('\n❌ Migration failed:', err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });