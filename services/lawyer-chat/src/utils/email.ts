// Email utility for sending verification emails
// In production, integrate with Outlook/Office 365 SMTP or SendGrid

import nodemailer from 'nodemailer';
import type { Transporter } from 'nodemailer';
import { logger } from '@/utils/logger';
import { config } from '@/lib/config';

export async function sendVerificationEmail(email: string, token: string) {
  const verificationUrl = `${process.env.NEXTAUTH_URL}/api/auth/verify?email=${encodeURIComponent(email)}&token=${token}`;
  
  // For development/demo, just log the URL
  if (process.env.NODE_ENV === 'development') {
    logger.emailDebug('VERIFICATION EMAIL', {
      To: email,
      'Verification URL': verificationUrl
    });
    return;
  }

  // Create email transporter
  let transporter: Transporter;
  
  try {
    // For production, use actual SMTP configuration
    if (process.env.SMTP_USER && process.env.SMTP_PASS) {
      transporter = nodemailer.createTransport({
        host: process.env.SMTP_HOST || 'smtp.office365.com',
        port: parseInt(process.env.SMTP_PORT || '587'),
        secure: process.env.SMTP_PORT === '465', // true for 465, false for other ports
        auth: {
          user: process.env.SMTP_USER,
          pass: process.env.SMTP_PASS
        },
        tls: {
          minVersion: 'TLSv1.2',
          rejectUnauthorized: true
        }
      });
    } else {
      // For development/testing, use Ethereal Email
      const testAccount = await nodemailer.createTestAccount();
      transporter = nodemailer.createTransport({
        host: 'smtp.ethereal.email',
        port: 587,
        secure: false,
        auth: {
          user: testAccount.user,
          pass: testAccount.pass
        }
      });
    }

    const emailContent = {
    from: config.email.from,
    to: email,
    subject: 'Verify your AI Legal account',
    html: `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background-color: #004A84; color: white; padding: 20px; text-align: center; }
            .content { background-color: #f4f4f4; padding: 30px; }
            .button { 
              display: inline-block; 
              padding: 12px 30px; 
              background-color: #C7A562; 
              color: #004A84; 
              text-decoration: none; 
              border-radius: 5px; 
              font-weight: bold;
              margin: 20px 0;
            }
            .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>AI Legal - Email Verification</h1>
            </div>
            <div class="content">
              <h2>Welcome to AI Legal!</h2>
              <p>Thank you for registering with AI Legal. To complete your registration and access the platform, please verify your email address.</p>
              
              <p style="text-align: center;">
                <a href="${verificationUrl}" class="button">Verify Email Address</a>
              </p>
              
              <p>Or copy and paste this link into your browser:</p>
              <p style="word-break: break-all; background: #fff; padding: 10px; border: 1px solid #ddd;">
                ${verificationUrl}
              </p>
              
              <p><strong>This link will expire in 24 hours.</strong></p>
              
              <p>If you didn&apos;t create an account with AI Legal, please ignore this email.</p>
            </div>
            <div class="footer">
              <p>© 2024 Reichman Jorgensen LLP. All rights reserved.</p>
              <p>This is an automated email. Please do not reply.</p>
            </div>
          </div>
        </body>
      </html>
    `,
    text: `
      Welcome to AI Legal!
      
      Thank you for registering. Please verify your email address by clicking the link below:
      
      ${verificationUrl}
      
      This link will expire in 24 hours.
      
      If you didn&apos;t create an account, please ignore this email.
    `
  };

    // Send the email
    const info = await transporter.sendMail(emailContent);
    
    // If using test account, log the preview URL
    if (!process.env.SMTP_USER) {
      logger.emailDebug('EMAIL SENT (Test Mode)', {
        'Preview URL': nodemailer.getTestMessageUrl(info)
      });
    }
    
    return info;
    
  } catch (error) {
    logger.error('Email sending error', error, { email });
    
    // In production without SMTP config, throw error
    if (process.env.NODE_ENV === 'production' && !process.env.SMTP_USER) {
      throw new Error('Email configuration not set up');
    }
    
    // Otherwise, rethrow the error
    throw error;
  }
}

export async function sendPasswordResetEmail(email: string, token: string) {
  const resetUrl = `${process.env.NEXTAUTH_URL}/auth/reset-password?token=${encodeURIComponent(token)}`;
  
  // For development, just log the URL
  if (process.env.NODE_ENV === 'development') {
    logger.emailDebug('PASSWORD RESET EMAIL', {
      To: email,
      'Reset URL': resetUrl
    });
    return;
  }

  // Create email transporter (same as verification email)
  let transporter: Transporter;
  
  try {
    if (process.env.SMTP_USER && process.env.SMTP_PASS) {
      transporter = nodemailer.createTransport({
        host: process.env.SMTP_HOST || 'smtp.office365.com',
        port: parseInt(process.env.SMTP_PORT || '587'),
        secure: process.env.SMTP_PORT === '465',
        auth: {
          user: process.env.SMTP_USER,
          pass: process.env.SMTP_PASS
        },
        tls: {
          minVersion: 'TLSv1.2',
          rejectUnauthorized: true
        }
      });
    } else {
      const testAccount = await nodemailer.createTestAccount();
      transporter = nodemailer.createTransport({
        host: 'smtp.ethereal.email',
        port: 587,
        secure: false,
        auth: {
          user: testAccount.user,
          pass: testAccount.pass
        }
      });
    }

    const emailContent = {
      from: config.email.from,
      to: email,
      subject: 'Reset your AI Legal password',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background-color: #004A84; color: white; padding: 20px; text-align: center; }
              .content { background-color: #f4f4f4; padding: 30px; }
              .button { 
                display: inline-block; 
                padding: 12px 30px; 
                background-color: #C7A562; 
                color: #004A84; 
                text-decoration: none; 
                border-radius: 5px; 
                font-weight: bold;
                margin: 20px 0;
              }
              .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>AI Legal - Password Reset</h1>
              </div>
              <div class="content">
                <h2>Password Reset Request</h2>
                <p>We received a request to reset your password for your AI Legal account.</p>
                
                <p style="text-align: center;">
                  <a href="${resetUrl}" class="button">Reset Password</a>
                </p>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #fff; padding: 10px; border: 1px solid #ddd;">
                  ${resetUrl}
                </p>
                
                <p><strong>This link will expire in 1 hour.</strong></p>
                
                <p>If you didn&apos;t request a password reset, please ignore this email. Your password will remain unchanged.</p>
              </div>
              <div class="footer">
                <p>© 2024 Reichman Jorgensen LLP. All rights reserved.</p>
                <p>This is an automated email. Please do not reply.</p>
              </div>
            </div>
          </body>
        </html>
      `,
      text: `
        Password Reset Request
        
        We received a request to reset your password for your AI Legal account.
        
        Reset your password by clicking the link below:
        
        ${resetUrl}
        
        This link will expire in 1 hour.
        
        If you didn&apos;t request a password reset, please ignore this email.
      `
    };

    const info = await transporter.sendMail(emailContent);
    
    if (!process.env.SMTP_USER) {
      logger.emailDebug('EMAIL SENT (Test Mode)', {
        'Preview URL': nodemailer.getTestMessageUrl(info)
      });
    }
    
    return info;
    
  } catch (error) {
    logger.error('Password reset email error', error, { email });
    if (process.env.NODE_ENV === 'production' && !process.env.SMTP_USER) {
      throw new Error('Email configuration not set up');
    }
    throw error;
  }
}