import { NextRequest } from 'next/server';
import { hash } from 'bcryptjs';
import prisma from '@/lib/prisma';
import { validateEmailDomain } from '@/utils/validation';
import crypto from 'crypto';
import { sendVerificationEmail } from '@/utils/email';
import { createLogger } from '@/utils/logger';
import { config, isAllowedEmailDomain, getAllowedDomainsForDisplay } from '@/lib/config';
import { retryWithBackoff } from '@/lib/retryUtils';

const logger = createLogger('register-api');

// Password requirements
const PASSWORD_MIN_LENGTH = config.security.passwordMinLength;
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;

export async function POST(request: NextRequest) {
  let email: string | undefined;
  
  try {
    const body = await request.json();
    email = body.email;
    const { password, confirmPassword, name } = body;

    // Normalize email early
    const userEmail = email?.toLowerCase() || '';

    // Validate email domain
    if (!email || !isAllowedEmailDomain(email)) {
      return new Response(
        JSON.stringify({ 
          error: `Only ${getAllowedDomainsForDisplay()} email addresses are allowed` 
        }), 
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Validate password
    if (!password || password.length < PASSWORD_MIN_LENGTH) {
      return new Response(
        JSON.stringify({ 
          error: `Password must be at least ${PASSWORD_MIN_LENGTH} characters long` 
        }), 
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (!PASSWORD_REGEX.test(password)) {
      return new Response(
        JSON.stringify({ 
          error: 'Password must contain uppercase, lowercase, number, and special character' 
        }), 
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (password !== confirmPassword) {
      return new Response(
        JSON.stringify({ error: 'Passwords do not match' }), 
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Check if user already exists
    const existingUser = await prisma.user.findUnique({
      where: { email: userEmail }
    });

    if (existingUser) {
      // Log the attempt but return success to prevent enumeration
      await prisma.auditLog.create({
        data: {
          action: 'REGISTRATION_DUPLICATE',
          email: userEmail,
          ipAddress: request.headers.get('x-forwarded-for') || 'unknown',
          userAgent: request.headers.get('user-agent') || 'unknown',
          success: false,
          errorMessage: 'Attempted to register existing email'
        }
      });
      
      // Return success message to prevent user enumeration
      return new Response(
        JSON.stringify({ 
          message: 'Registration successful! Please check your email to verify your account.',
          email: userEmail
        }), 
        { status: 201, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Generate verification token
    const verificationToken = crypto.randomBytes(32).toString('hex');
    const verificationExpires = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours

    // Hash password
    const hashedPassword = await hash(password, 12);

    // Create user with unverified status
    const user = await prisma.user.create({
      data: {
        email: userEmail,
        name: name || userEmail.split('@')[0],
        password: hashedPassword,
        emailVerified: null, // Not verified yet
        registrationToken: verificationToken,
        registrationTokenExpires: verificationExpires,
        registrationIp: request.headers.get('x-forwarded-for') || 'unknown',
        role: 'user'
      }
    });

    // Send verification email with retry mechanism
    let emailSent = false;
    try {
      await retryWithBackoff(
        async () => sendVerificationEmail(userEmail, verificationToken),
        {
          maxAttempts: 3,
          initialDelay: 1000,
          onRetry: (attempt, error) => {
            logger.warn(`Email send attempt ${attempt} failed for ${userEmail}`, { 
              attempt, 
              error: error.message,
              userId: user.id 
            });
          }
        }
      );
      emailSent = true;
    } catch (emailError) {
      // Log email failure but don't delete user - they can request resend later
      logger.error('All email send attempts failed', emailError, { 
        email: userEmail, 
        userId: user.id,
        action: 'REGISTRATION_EMAIL_FAILED'
      });
      
      // Create audit log for failed email
      await prisma.auditLog.create({
        data: {
          action: 'REGISTRATION_EMAIL_FAILED',
          userId: user.id,
          email: userEmail,
          ipAddress: request.headers.get('x-forwarded-for') || 'unknown',
          userAgent: request.headers.get('user-agent') || 'unknown',
          success: false,
          errorMessage: emailError instanceof Error ? emailError.message : 'Email send failed',
          metadata: { requiresManualIntervention: true }
        }
      });
    }

    // Log registration attempt for admin monitoring
    await prisma.auditLog.create({
      data: {
        action: 'USER_REGISTRATION',
        userId: user.id,
        email: userEmail,
        ipAddress: request.headers.get('x-forwarded-for') || 'unknown',
        userAgent: request.headers.get('user-agent') || 'unknown',
        success: true,
        metadata: { emailSent: emailSent }
      }
    });

    // Return appropriate response based on email status
    if (emailSent) {
      return new Response(
        JSON.stringify({ 
          message: 'Registration successful! Please check your email to verify your account.',
          email: userEmail
        }), 
        { status: 201, headers: { 'Content-Type': 'application/json' } }
      );
    } else {
      // Registration succeeded but email failed - still return success
      // User can request verification email resend later
      return new Response(
        JSON.stringify({ 
          message: 'Registration successful! However, we had trouble sending the verification email. You can request a new verification email from the login page.',
          email: userEmail,
          emailSent: false
        }), 
        { status: 201, headers: { 'Content-Type': 'application/json' } }
      );
    }

  } catch (error) {
    logger.error('Registration error', error, { email });
    
    // Log failed registration attempt
    try {
      await prisma.auditLog.create({
        data: {
          action: 'USER_REGISTRATION',
          email: email || 'unknown',
          ipAddress: request.headers.get('x-forwarded-for') || 'unknown',
          userAgent: request.headers.get('user-agent') || 'unknown',
          success: false,
          errorMessage: error instanceof Error ? error.message : 'Unknown error'
        }
      });
    } catch (logError) {
      // If logging fails, don't throw - just log silently
      // Silent fail to avoid recursive logging
    }

    return new Response(
      JSON.stringify({ error: 'Registration failed. Please try again.' }), 
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}