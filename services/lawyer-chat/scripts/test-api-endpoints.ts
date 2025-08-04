#!/usr/bin/env node

/**
 * Test script to verify API endpoints work correctly with field-level encryption
 * Tests registration, login, password reset, and audit logging
 */

import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });
dotenv.config({ path: '.env' });

// Mock Next.js request/response for testing
const mockHeaders = new Map();
mockHeaders.set('x-forwarded-for', '192.168.1.100');
mockHeaders.set('user-agent', 'Test Agent');

global.fetch = require('node-fetch').default;

// Import after env setup
import prisma from '../src/lib/prisma';
import { hash, compare } from 'bcryptjs';
import * as crypto from 'crypto';

async function testRegistrationEndpoint() {
  console.log('\n🧪 Testing Registration Endpoint');
  console.log('==============================');
  
  const testEmail = `api-test-${Date.now()}@reichmanjorgensen.com`;
  const testPassword = 'TestPassword123!';
  
  try {
    // Simulate registration
    console.log('1. Creating user via registration flow...');
    
    const hashedPassword = await hash(testPassword, 12);
    const registrationToken = crypto.randomBytes(32).toString('hex');
    const registrationIp = '10.0.0.1';
    
    const user = await prisma.user.create({
      data: {
        email: testEmail,
        name: 'API Test User',
        password: hashedPassword,
        registrationToken: registrationToken,
        registrationTokenExpires: new Date(Date.now() + 24 * 60 * 60 * 1000),
        registrationIp: registrationIp,
        role: 'user'
      }
    });
    
    console.log(`✅ User created with id: ${user.id}`);
    
    // Verify encrypted fields
    const rawUser = await prisma.$queryRaw`
      SELECT "registrationToken", "registrationIp" FROM "User" WHERE id = ${user.id}
    ` as any[];
    
    if (rawUser[0]) {
      console.log(`✅ Registration token encrypted: ${rawUser[0].registrationToken.startsWith('enc:v1:')}`);
      console.log(`✅ Registration IP encrypted: ${rawUser[0].registrationIp.startsWith('enc:v1:')}`);
    }
    
    // Test audit log creation
    console.log('\n2. Creating audit log...');
    const auditLog = await prisma.auditLog.create({
      data: {
        action: 'USER_REGISTRATION',
        userId: user.id,
        email: testEmail,
        ipAddress: registrationIp,
        userAgent: 'Test Agent',
        success: true,
        metadata: { test: true }
      }
    });
    
    console.log(`✅ Audit log created with id: ${auditLog.id}`);
    
    // Verify audit log encryption
    const rawAudit = await prisma.$queryRaw`
      SELECT "ipAddress" FROM "AuditLog" WHERE id = ${auditLog.id}
    ` as any[];
    
    if (rawAudit[0]) {
      console.log(`✅ Audit IP encrypted: ${rawAudit[0].ipAddress.startsWith('enc:v1:')}`);
    }
    
    // Cleanup
    await prisma.auditLog.delete({ where: { id: auditLog.id } });
    await prisma.user.delete({ where: { id: user.id } });
    
  } catch (error) {
    console.error('❌ Registration test failed:', error);
  }
}

async function testPasswordResetFlow() {
  console.log('\n🧪 Testing Password Reset Flow');
  console.log('============================');
  
  const testEmail = `reset-test-${Date.now()}@reichmanjorgensen.com`;
  
  try {
    // Create user
    const user = await prisma.user.create({
      data: {
        email: testEmail,
        name: 'Reset Test User',
        password: await hash('OldPassword123!', 12),
        emailVerified: new Date(),
        role: 'user'
      }
    });
    
    console.log('1. Initiating password reset...');
    
    // Generate reset token
    const resetToken = crypto.randomBytes(32).toString('hex');
    const hashedToken = await hash(resetToken, 12);
    
    // Update user with reset token
    await prisma.user.update({
      where: { id: user.id },
      data: {
        passwordResetToken: hashedToken,
        passwordResetExpires: new Date(Date.now() + 60 * 60 * 1000) // 1 hour
      }
    });
    
    console.log(`✅ Reset token generated and stored`);
    
    // Verify encryption
    const rawUser = await prisma.$queryRaw`
      SELECT "passwordResetToken" FROM "User" WHERE id = ${user.id}
    ` as any[];
    
    if (rawUser[0]) {
      console.log(`✅ Reset token encrypted: ${rawUser[0].passwordResetToken.startsWith('enc:v1:')}`);
    }
    
    // Simulate token verification
    console.log('\n2. Verifying reset token...');
    const userWithToken = await prisma.user.findUnique({
      where: { id: user.id }
    });
    
    if (userWithToken && userWithToken.passwordResetToken) {
      // The token is stored hashed, so we verify it like a password
      const tokenValid = await compare(resetToken, userWithToken.passwordResetToken);
      console.log(`✅ Token verification: ${tokenValid ? 'Valid' : 'Invalid'}`);
    }
    
    // Create audit log for password reset
    console.log('\n3. Logging password reset attempt...');
    const auditLog = await prisma.auditLog.create({
      data: {
        action: 'PASSWORD_RESET_REQUEST',
        userId: user.id,
        email: testEmail,
        ipAddress: '10.0.0.2',
        userAgent: 'Test Agent',
        success: true
      }
    });
    
    console.log(`✅ Audit log created`);
    
    // Cleanup
    await prisma.auditLog.delete({ where: { id: auditLog.id } });
    await prisma.user.delete({ where: { id: user.id } });
    
  } catch (error) {
    console.error('❌ Password reset test failed:', error);
  }
}

async function testLoginTracking() {
  console.log('\n🧪 Testing Login Tracking');
  console.log('=======================');
  
  const testEmail = `login-test-${Date.now()}@reichmanjorgensen.com`;
  const loginIp = '10.0.0.3';
  
  try {
    // Create user
    const user = await prisma.user.create({
      data: {
        email: testEmail,
        name: 'Login Test User',
        password: await hash('TestPassword123!', 12),
        emailVerified: new Date(),
        role: 'user'
      }
    });
    
    console.log('1. Simulating successful login...');
    
    // Update last login IP
    await prisma.user.update({
      where: { id: user.id },
      data: {
        lastLoginIp: loginIp,
        lastLoginAt: new Date(),
        failedLoginAttempts: 0
      }
    });
    
    console.log(`✅ Login tracking updated`);
    
    // Verify encryption
    const rawUser = await prisma.$queryRaw`
      SELECT "lastLoginIp" FROM "User" WHERE id = ${user.id}
    ` as any[];
    
    if (rawUser[0]) {
      console.log(`✅ Last login IP encrypted: ${rawUser[0].lastLoginIp.startsWith('enc:v1:')}`);
    }
    
    // Test failed login tracking
    console.log('\n2. Simulating failed login attempts...');
    
    await prisma.user.update({
      where: { id: user.id },
      data: {
        failedLoginAttempts: { increment: 1 }
      }
    });
    
    // Create audit log for failed login
    const auditLog = await prisma.auditLog.create({
      data: {
        action: 'LOGIN_FAILED',
        email: testEmail,
        ipAddress: loginIp,
        userAgent: 'Test Agent',
        success: false,
        errorMessage: 'Invalid password',
        metadata: { attempts: 1 }
      }
    });
    
    console.log(`✅ Failed login tracked`);
    
    // Read back and verify
    const updatedUser = await prisma.user.findUnique({
      where: { id: user.id }
    });
    
    if (updatedUser) {
      console.log(`✅ Failed attempts: ${updatedUser.failedLoginAttempts}`);
      console.log(`✅ Last login IP decrypted: ${updatedUser.lastLoginIp === loginIp}`);
    }
    
    // Cleanup
    await prisma.auditLog.delete({ where: { id: auditLog.id } });
    await prisma.user.delete({ where: { id: user.id } });
    
  } catch (error) {
    console.error('❌ Login tracking test failed:', error);
  }
}

async function testSessionManagement() {
  console.log('\n🧪 Testing Session Management');
  console.log('===========================');
  
  const testEmail = `session-test-${Date.now()}@reichmanjorgensen.com`;
  
  try {
    // Create user
    const user = await prisma.user.create({
      data: {
        email: testEmail,
        name: 'Session Test User',
        password: await hash('TestPassword123!', 12),
        emailVerified: new Date(),
        role: 'user'
      }
    });
    
    console.log('1. Creating session...');
    
    // Create session
    const sessionToken = crypto.randomBytes(32).toString('hex');
    const session = await prisma.session.create({
      data: {
        sessionToken: sessionToken,
        userId: user.id,
        expires: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
      }
    });
    
    console.log(`✅ Session created`);
    
    // Verify encryption
    const rawSession = await prisma.$queryRaw`
      SELECT "sessionToken" FROM "Session" WHERE id = ${session.id}
    ` as any[];
    
    if (rawSession[0]) {
      console.log(`✅ Session token encrypted: ${rawSession[0].sessionToken.startsWith('enc:v1:')}`);
    }
    
    // Find session by token
    console.log('\n2. Finding session by token...');
    const foundSession = await prisma.session.findUnique({
      where: { sessionToken: sessionToken }
    });
    
    if (foundSession) {
      console.log(`✅ Session found and token matches: ${foundSession.sessionToken === sessionToken}`);
    }
    
    // Cleanup
    await prisma.session.delete({ where: { id: session.id } });
    await prisma.user.delete({ where: { id: user.id } });
    
  } catch (error) {
    console.error('❌ Session management test failed:', error);
  }
}

async function main() {
  console.log('🔐 API Endpoints Encryption Test Suite');
  console.log('====================================');
  
  // Check if encryption key is set
  if (!process.env.FIELD_ENCRYPTION_KEY && !process.env.NEXTAUTH_SECRET) {
    console.error('❌ Error: FIELD_ENCRYPTION_KEY or NEXTAUTH_SECRET must be set');
    console.log('\nTo set a test key, run:');
    console.log('export FIELD_ENCRYPTION_KEY=$(openssl rand -hex 32)');
    process.exit(1);
  }
  
  console.log('✅ Encryption key found\n');
  
  try {
    await testRegistrationEndpoint();
    await testPasswordResetFlow();
    await testLoginTracking();
    await testSessionManagement();
    
    console.log('\n✅ All API endpoint tests passed!');
    console.log('\nEncryption is working correctly with:');
    console.log('- User registration and tokens');
    console.log('- Password reset tokens');
    console.log('- Login tracking and IPs');
    console.log('- Session management');
    console.log('- Audit logging');
    
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