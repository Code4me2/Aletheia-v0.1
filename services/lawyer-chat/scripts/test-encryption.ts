#!/usr/bin/env node

/**
 * Test script for field-level encryption
 * Tests encryption/decryption functionality and database operations
 */

import { encrypt, decrypt, needsEncryption, shouldEncryptField, ENCRYPTED_FIELDS } from '../src/lib/crypto';
import prisma from '../src/lib/prisma';
import * as crypto from 'crypto';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });
dotenv.config({ path: '.env' });

// Test data
const testData = {
  shortText: 'test123',
  longText: 'This is a longer test string with special characters: !@#$%^&*()_+{}[]|":;<>?,./~`',
  ipAddress: '192.168.1.100',
  token: crypto.randomBytes(32).toString('hex'),
  emptyString: '',
  nullValue: null,
  undefinedValue: undefined
};

async function testBasicEncryption() {
  console.log('\n🧪 Testing Basic Encryption/Decryption');
  console.log('=====================================');
  
  for (const [name, value] of Object.entries(testData)) {
    console.log(`\nTesting: ${name}`);
    console.log(`Original: ${value}`);
    
    try {
      const encrypted = encrypt(value as string);
      console.log(`Encrypted: ${encrypted ? encrypted.substring(0, 50) + '...' : encrypted}`);
      
      const decrypted = decrypt(encrypted);
      console.log(`Decrypted: ${decrypted}`);
      
      if (value === decrypted) {
        console.log('✅ Match!');
      } else {
        console.log('❌ Mismatch!');
      }
      
      if (encrypted && needsEncryption(encrypted)) {
        console.log('❌ needsEncryption returned true for encrypted value');
      } else if (value && !needsEncryption(value as string)) {
        console.log('❌ needsEncryption returned false for unencrypted value');
      }
      
    } catch (error) {
      console.log(`❌ Error: ${error}`);
    }
  }
}

async function testFieldDetection() {
  console.log('\n🧪 Testing Field Detection');
  console.log('========================');
  
  for (const [model, fields] of Object.entries(ENCRYPTED_FIELDS)) {
    console.log(`\n${model}:`);
    for (const field of fields) {
      const shouldEncrypt = shouldEncryptField(model, field);
      console.log(`  ${field}: ${shouldEncrypt ? '✅ Should encrypt' : '❌ Should not encrypt'}`);
    }
    
    // Test non-encrypted field
    const shouldNotEncrypt = shouldEncryptField(model, 'id');
    console.log(`  id: ${shouldNotEncrypt ? '❌ Should encrypt (incorrect)' : '✅ Should not encrypt'}`);
  }
}

async function testDatabaseOperations() {
  console.log('\n🧪 Testing Database Operations');
  console.log('============================');
  
  const testEmail = `encryption-test-${Date.now()}@test.com`;
  const testIp = '10.0.0.1';
  const testToken = crypto.randomBytes(32).toString('hex');
  
  try {
    // Test creating an audit log with encrypted IP
    console.log('\n1. Creating AuditLog with encrypted IP address...');
    const auditLog = await prisma.auditLog.create({
      data: {
        action: 'ENCRYPTION_TEST',
        email: testEmail,
        ipAddress: testIp,
        userAgent: 'Test Agent',
        success: true,
        metadata: { test: true }
      }
    });
    console.log(`✅ Created AuditLog with id: ${auditLog.id}`);
    
    // Read it back
    console.log('\n2. Reading AuditLog back...');
    const readAuditLog = await prisma.auditLog.findUnique({
      where: { id: auditLog.id }
    });
    
    if (readAuditLog) {
      console.log(`  IP Address matches: ${readAuditLog.ipAddress === testIp ? '✅' : '❌'}`);
      console.log(`  Decrypted IP: ${readAuditLog.ipAddress}`);
      
      // Check raw database value
      const rawAuditLog = await prisma.$queryRaw`
        SELECT "ipAddress" FROM "AuditLog" WHERE id = ${auditLog.id}
      ` as any[];
      
      if (rawAuditLog[0]) {
        console.log(`  Raw DB value: ${rawAuditLog[0].ipAddress.substring(0, 50)}...`);
        console.log(`  Is encrypted: ${!needsEncryption(rawAuditLog[0].ipAddress) ? '✅' : '❌'}`);
      }
    }
    
    // Test user with encrypted fields
    console.log('\n3. Creating User with encrypted tokens and IPs...');
    const user = await prisma.user.create({
      data: {
        email: testEmail,
        name: 'Encryption Test User',
        password: 'hashed_password_here',
        registrationToken: testToken,
        registrationTokenExpires: new Date(Date.now() + 24 * 60 * 60 * 1000),
        registrationIp: testIp,
        role: 'user'
      }
    });
    console.log(`✅ Created User with id: ${user.id}`);
    
    // Read user back
    console.log('\n4. Reading User back...');
    const readUser = await prisma.user.findUnique({
      where: { id: user.id }
    });
    
    if (readUser) {
      console.log(`  Registration token matches: ${readUser.registrationToken === testToken ? '✅' : '❌'}`);
      console.log(`  Registration IP matches: ${readUser.registrationIp === testIp ? '✅' : '❌'}`);
      
      // Check raw database values
      const rawUser = await prisma.$queryRaw`
        SELECT "registrationToken", "registrationIp" FROM "User" WHERE id = ${user.id}
      ` as any[];
      
      if (rawUser[0]) {
        console.log(`  Raw token encrypted: ${!needsEncryption(rawUser[0].registrationToken) ? '✅' : '❌'}`);
        console.log(`  Raw IP encrypted: ${!needsEncryption(rawUser[0].registrationIp) ? '✅' : '❌'}`);
      }
    }
    
    // Test update operation
    console.log('\n5. Testing update operation...');
    const newIp = '10.0.0.2';
    await prisma.user.update({
      where: { id: user.id },
      data: { lastLoginIp: newIp }
    });
    
    const updatedUser = await prisma.user.findUnique({
      where: { id: user.id }
    });
    
    if (updatedUser) {
      console.log(`  Last login IP matches: ${updatedUser.lastLoginIp === newIp ? '✅' : '❌'}`);
    }
    
    // Test batch operations
    console.log('\n6. Testing batch operations...');
    const users = await prisma.user.findMany({
      where: { email: testEmail }
    });
    console.log(`  Found ${users.length} users`);
    console.log(`  All IPs decrypted: ${users.every(u => u.registrationIp === testIp) ? '✅' : '❌'}`);
    
    // Cleanup
    console.log('\n7. Cleaning up test data...');
    await prisma.auditLog.delete({ where: { id: auditLog.id } });
    await prisma.user.delete({ where: { id: user.id } });
    console.log('✅ Cleanup completed');
    
  } catch (error) {
    console.error('❌ Database operation failed:', error);
  }
}

async function testPerformance() {
  console.log('\n🧪 Testing Performance');
  console.log('====================');
  
  const iterations = 1000;
  const testString = 'Performance test string with some length to it';
  
  // Test encryption performance
  console.log(`\nEncrypting ${iterations} times...`);
  const encryptStart = Date.now();
  let encrypted = '';
  for (let i = 0; i < iterations; i++) {
    encrypted = encrypt(testString) || '';
  }
  const encryptTime = Date.now() - encryptStart;
  console.log(`✅ Encryption: ${encryptTime}ms (${(encryptTime/iterations).toFixed(2)}ms per operation)`);
  
  // Test decryption performance
  console.log(`\nDecrypting ${iterations} times...`);
  const decryptStart = Date.now();
  for (let i = 0; i < iterations; i++) {
    decrypt(encrypted);
  }
  const decryptTime = Date.now() - decryptStart;
  console.log(`✅ Decryption: ${decryptTime}ms (${(decryptTime/iterations).toFixed(2)}ms per operation)`);
}

async function main() {
  console.log('🔐 Field-Level Encryption Test Suite');
  console.log('===================================');
  
  // Check if encryption key is set
  if (!process.env.FIELD_ENCRYPTION_KEY && !process.env.NEXTAUTH_SECRET) {
    console.error('❌ Error: FIELD_ENCRYPTION_KEY or NEXTAUTH_SECRET must be set');
    console.log('\nTo set a test key, run:');
    console.log('export FIELD_ENCRYPTION_KEY=$(openssl rand -hex 32)');
    process.exit(1);
  }
  
  console.log('✅ Encryption key found');
  
  try {
    await testBasicEncryption();
    await testFieldDetection();
    await testDatabaseOperations();
    await testPerformance();
    
    console.log('\n✅ All tests completed successfully!');
    
  } catch (error) {
    console.error('\n❌ Test suite failed:', error);
    process.exit(1);
  }
}

main()
  .catch(console.error)
  .finally(async () => {
    await prisma.$disconnect();
  });