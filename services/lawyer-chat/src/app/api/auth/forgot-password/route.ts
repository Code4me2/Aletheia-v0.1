import { NextRequest, NextResponse } from 'next/server';
import { randomBytes } from 'crypto';
import bcrypt from 'bcryptjs';
import prisma from '@/lib/prisma';
import { sendPasswordResetEmail } from '@/utils/email';
import { createLogger } from '@/utils/logger';
import { config, isAllowedEmailDomain } from '@/lib/config';

const logger = createLogger('forgot-password-api');

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json();

    if (!email) {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }

    // Check if email is from allowed domain
    if (!isAllowedEmailDomain(email)) {
      // Return success even for non-allowed domains to prevent email enumeration
      return NextResponse.json({
        message: 'If an account exists with this email, a password reset link has been sent.'
      });
    }

    // Find user by email
    const user = await prisma.user.findUnique({
      where: { email },
      select: {
        id: true,
        email: true,
        emailVerified: true,
        lockedUntil: true
      }
    });

    // Always return success to prevent email enumeration
    if (!user) {
      // Log attempt for non-existent user
      await prisma.auditLog.create({
        data: {
          action: 'password_reset_request',
          email,
          ipAddress: request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown',
          userAgent: request.headers.get('user-agent') || 'unknown',
          success: false,
          errorMessage: 'User not found'
        }
      });

      return NextResponse.json({
        message: 'If an account exists with this email, a password reset link has been sent.'
      });
    }

    // Check if account is locked
    if (user.lockedUntil && user.lockedUntil > new Date()) {
      // Log attempt for locked account
      await prisma.auditLog.create({
        data: {
          action: 'password_reset_request',
          userId: user.id,
          email: user.email,
          ipAddress: request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown',
          userAgent: request.headers.get('user-agent') || 'unknown',
          success: false,
          errorMessage: 'Account locked'
        }
      });

      return NextResponse.json({
        message: 'If an account exists with this email, a password reset link has been sent.'
      });
    }

    // Check if email is verified
    if (!user.emailVerified) {
      // Log attempt for unverified email
      await prisma.auditLog.create({
        data: {
          action: 'password_reset_request',
          userId: user.id,
          email: user.email,
          ipAddress: request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown',
          userAgent: request.headers.get('user-agent') || 'unknown',
          success: false,
          errorMessage: 'Email not verified'
        }
      });

      return NextResponse.json({
        message: 'If an account exists with this email, a password reset link has been sent.'
      });
    }

    // Generate secure reset token
    const resetToken = randomBytes(32).toString('hex');
    const hashedToken = await bcrypt.hash(resetToken, 10);

    // Set expiry based on config
    const resetExpiry = new Date();
    resetExpiry.setHours(resetExpiry.getHours() + config.security.resetTokenExpiryHours);

    // Update user with reset token
    await prisma.user.update({
      where: { id: user.id },
      data: {
        passwordResetToken: hashedToken,
        passwordResetExpires: resetExpiry
      }
    });

    // Send password reset email
    try {
      await sendPasswordResetEmail(user.email!, resetToken);
    } catch (emailError) {
      logger.error('Failed to send password reset email', emailError);
      
      // Clean up token if email fails
      await prisma.user.update({
        where: { id: user.id },
        data: {
          passwordResetToken: null,
          passwordResetExpires: null
        }
      });

      // Log failed email attempt
      await prisma.auditLog.create({
        data: {
          action: 'password_reset_request',
          userId: user.id,
          email: user.email,
          ipAddress: request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown',
          userAgent: request.headers.get('user-agent') || 'unknown',
          success: false,
          errorMessage: 'Failed to send email'
        }
      });

      return NextResponse.json(
        { error: 'Failed to send password reset email. Please try again later.' },
        { status: 500 }
      );
    }

    // Log successful password reset request
    await prisma.auditLog.create({
      data: {
        action: 'password_reset_request',
        userId: user.id,
        email: user.email,
        ipAddress: request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown',
        userAgent: request.headers.get('user-agent') || 'unknown',
        success: true
      }
    });

    return NextResponse.json({
      message: 'If an account exists with this email, a password reset link has been sent.'
    });

  } catch (error) {
    logger.error('Password reset request error', error);
    return NextResponse.json(
      { error: 'An error occurred. Please try again later.' },
      { status: 500 }
    );
  }
}