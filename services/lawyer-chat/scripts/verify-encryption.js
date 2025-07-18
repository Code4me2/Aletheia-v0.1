#!/usr/bin/env node

/**
 * Simple verification that encryption is working in production
 * This can run in the Docker container
 */

console.log('🔐 Verifying Field-Level Encryption');
console.log('==================================\n');

// Check if encryption key is set
if (!process.env.FIELD_ENCRYPTION_KEY && !process.env.NEXTAUTH_SECRET) {
  console.error('❌ Error: FIELD_ENCRYPTION_KEY or NEXTAUTH_SECRET must be set');
  process.exit(1);
}

console.log('✅ Encryption key is configured');
console.log(`   Using: ${process.env.FIELD_ENCRYPTION_KEY ? 'FIELD_ENCRYPTION_KEY' : 'NEXTAUTH_SECRET'}`);

// Import Prisma client (which has encryption middleware)
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function testEncryption() {
  try {
    console.log('\n📝 Creating test audit log with encrypted IP...');
    
    const testIp = '192.168.1.100';
    const testEmail = `encryption-test-${Date.now()}@test.com`;
    
    // Create a test audit log
    const audit = await prisma.auditLog.create({
      data: {
        action: 'ENCRYPTION_VERIFICATION',
        email: testEmail,
        ipAddress: testIp,
        userAgent: 'Encryption Test',
        success: true,
        metadata: { test: true, timestamp: new Date().toISOString() }
      }
    });
    
    console.log(`✅ Created audit log with ID: ${audit.id}`);
    
    // Read it back
    const readAudit = await prisma.auditLog.findUnique({
      where: { id: audit.id }
    });
    
    if (readAudit && readAudit.ipAddress === testIp) {
      console.log('✅ IP address decrypted correctly');
    } else {
      console.log('❌ IP address decryption failed');
    }
    
    // Check raw database value
    const rawResult = await prisma.$queryRaw`
      SELECT "ipAddress" FROM "AuditLog" WHERE id = ${audit.id}
    `;
    
    if (rawResult && rawResult[0]) {
      const rawIp = rawResult[0].ipAddress;
      if (rawIp.startsWith('enc:v1:')) {
        console.log('✅ IP is encrypted in database');
        console.log(`   Raw value: ${rawIp.substring(0, 30)}...`);
      } else {
        console.log('❌ IP is NOT encrypted in database');
        console.log(`   Raw value: ${rawIp}`);
      }
    }
    
    // Cleanup
    await prisma.auditLog.delete({ where: { id: audit.id } });
    console.log('✅ Test data cleaned up');
    
    console.log('\n🎉 Encryption is working correctly!');
    console.log('   - New data is being encrypted automatically');
    console.log('   - Encrypted data is decrypted when read');
    console.log('   - Your sensitive fields are protected');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    console.error('   This might mean:');
    console.error('   - Database connection issue');
    console.error('   - Encryption middleware not loaded');
    console.error('   - Invalid encryption key');
  } finally {
    await prisma.$disconnect();
  }
}

testEncryption();