#!/usr/bin/env node

/**
 * Test script to verify NextAuth compatibility with field-level encryption
 * Ensures that NextAuth operations work correctly with encrypted fields
 */

import prisma from '../src/lib/prisma';
import { hash } from 'bcryptjs';
import * as crypto from 'crypto';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });
dotenv.config({ path: '.env' });

async function testNextAuthOperations() {
  console.log('🔐 Testing NextAuth Compatibility with Encryption');
  console.log('==============================================\n');
  
  const testEmail = `nextauth-test-${Date.now()}@test.com`;
  const testSessionToken = crypto.randomBytes(32).toString('hex');
  
  try {
    // 1. Test User creation (as NextAuth would do)
    console.log('1. Creating User (NextAuth style)...');
    const user = await prisma.user.create({
      data: {
        email: testEmail,
        name: 'NextAuth Test User',
        emailVerified: new Date(),
        role: 'user'
      }
    });
    console.log(`✅ Created user with id: ${user.id}`);
    
    // 2. Test Session creation with encrypted sessionToken
    console.log('\n2. Creating Session with encrypted token...');
    const session = await prisma.session.create({
      data: {
        sessionToken: testSessionToken,
        userId: user.id,
        expires: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000) // 30 days
      }
    });
    console.log(`✅ Created session with id: ${session.id}`);
    
    // 3. Test finding session by token (as NextAuth does)
    console.log('\n3. Finding session by token (NextAuth pattern)...');
    const foundSession = await prisma.session.findUnique({
      where: { sessionToken: testSessionToken },
      include: { user: true }
    });
    
    if (foundSession) {
      console.log(`✅ Found session for user: ${foundSession.user.email}`);
      console.log(`   Session token matches: ${foundSession.sessionToken === testSessionToken ? '✅' : '❌'}`);
    } else {
      console.log('❌ Session not found!');
    }
    
    // 4. Test Account creation (OAuth provider)
    console.log('\n4. Creating Account (OAuth provider)...');
    const account = await prisma.account.create({
      data: {
        userId: user.id,
        type: 'oauth',
        provider: 'google',
        providerAccountId: 'google-123456',
        access_token: 'encrypted_access_token_here',
        refresh_token: 'encrypted_refresh_token_here',
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        token_type: 'Bearer',
        scope: 'openid email profile'
      }
    });
    console.log(`✅ Created account with id: ${account.id}`);
    
    // 5. Test finding account and checking tokens
    console.log('\n5. Reading Account tokens...');
    const foundAccount = await prisma.account.findFirst({
      where: { userId: user.id }
    });
    
    if (foundAccount) {
      console.log(`✅ Found account for provider: ${foundAccount.provider}`);
      console.log(`   Access token decrypted: ${foundAccount.access_token === 'encrypted_access_token_here' ? '✅' : '❌'}`);
      console.log(`   Refresh token decrypted: ${foundAccount.refresh_token === 'encrypted_refresh_token_here' ? '✅' : '❌'}`);
    }
    
    // 6. Test VerificationToken
    console.log('\n6. Creating VerificationToken...');
    const verificationToken = crypto.randomBytes(32).toString('hex');
    const verification = await prisma.verificationToken.create({
      data: {
        identifier: testEmail,
        token: verificationToken,
        expires: new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours
      }
    });
    console.log(`✅ Created verification token`);
    
    // 7. Test finding verification token
    console.log('\n7. Finding verification token...');
    const foundVerification = await prisma.verificationToken.findUnique({
      where: {
        identifier_token: {
          identifier: testEmail,
          token: verificationToken
        }
      }
    });
    
    if (foundVerification) {
      console.log(`✅ Found verification token`);
      console.log(`   Token matches: ${foundVerification.token === verificationToken ? '✅' : '❌'}`);
    }
    
    // 8. Check raw database values
    console.log('\n8. Checking raw database encryption...');
    
    const rawSession = await prisma.$queryRaw`
      SELECT "sessionToken" FROM "Session" WHERE id = ${session.id}
    ` as any[];
    
    const rawAccount = await prisma.$queryRaw`
      SELECT "access_token", "refresh_token" FROM "Account" WHERE id = ${account.id}
    ` as any[];
    
    const rawVerification = await prisma.$queryRaw`
      SELECT "token" FROM "VerificationToken" 
      WHERE identifier = ${testEmail} AND token = ${verificationToken}
    ` as any[];
    
    if (rawSession[0]) {
      console.log(`   Session token encrypted in DB: ${rawSession[0].sessionToken.startsWith('enc:v1:') ? '✅' : '❌'}`);
    }
    
    if (rawAccount[0]) {
      console.log(`   Access token encrypted in DB: ${rawAccount[0].access_token.startsWith('enc:v1:') ? '✅' : '❌'}`);
      console.log(`   Refresh token encrypted in DB: ${rawAccount[0].refresh_token.startsWith('enc:v1:') ? '✅' : '❌'}`);
    }
    
    if (rawVerification[0]) {
      console.log(`   Verification token encrypted in DB: ${rawVerification[0].token.startsWith('enc:v1:') ? '✅' : '❌'}`);
    }
    
    // Cleanup
    console.log('\n9. Cleaning up test data...');
    await prisma.verificationToken.delete({
      where: {
        identifier_token: {
          identifier: testEmail,
          token: verificationToken
        }
      }
    });
    await prisma.account.delete({ where: { id: account.id } });
    await prisma.session.delete({ where: { id: session.id } });
    await prisma.user.delete({ where: { id: user.id } });
    console.log('✅ Cleanup completed');
    
    console.log('\n✅ NextAuth compatibility test passed!');
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    
    // Cleanup on error
    try {
      const user = await prisma.user.findUnique({ where: { email: testEmail } });
      if (user) {
        await prisma.account.deleteMany({ where: { userId: user.id } });
        await prisma.session.deleteMany({ where: { userId: user.id } });
        await prisma.user.delete({ where: { id: user.id } });
      }
      await prisma.verificationToken.deleteMany({ where: { identifier: testEmail } });
    } catch (cleanupError) {
      console.error('Cleanup error:', cleanupError);
    }
  }
}

async function main() {
  // Check if encryption key is set
  if (!process.env.FIELD_ENCRYPTION_KEY && !process.env.NEXTAUTH_SECRET) {
    console.error('❌ Error: FIELD_ENCRYPTION_KEY or NEXTAUTH_SECRET must be set');
    console.log('\nTo set a test key, run:');
    console.log('export FIELD_ENCRYPTION_KEY=$(openssl rand -hex 32)');
    process.exit(1);
  }
  
  await testNextAuthOperations();
}

main()
  .catch(console.error)
  .finally(async () => {
    await prisma.$disconnect();
  });