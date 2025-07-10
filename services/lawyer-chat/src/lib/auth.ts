import { AuthOptions, User } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { compare } from "bcryptjs";
import { PrismaAdapter } from "@next-auth/prisma-adapter";
import prisma from "@/lib/prisma";
import { config, isAllowedEmailDomain, getAllowedDomainsForDisplay } from "@/lib/config";

// Extend the User type to include role
interface ExtendedUser extends User {
  role: 'user' | 'admin';
}

// Maximum failed login attempts before lockout
const MAX_LOGIN_ATTEMPTS = config.security.maxLoginAttempts;
const LOCKOUT_DURATION = config.security.lockoutDuration;

export const authOptions: AuthOptions = {
  adapter: PrismaAdapter(prisma),
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials, req) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        const email = credentials.email.toLowerCase();
        const ipAddress = (req?.headers?.['x-forwarded-for'] || req?.headers?.['x-real-ip'] || 'unknown') as string;

        // Check if email is from allowed domains
        if (!isAllowedEmailDomain(email)) {
          throw new Error(`Only employees from ${getAllowedDomainsForDisplay()} can sign in`);
        }

        try {
          // Find user in database
          const user = await prisma.user.findUnique({
            where: { email }
          });

          if (!user || !user.password) {
            // Log failed attempt
            await prisma.auditLog.create({
              data: {
                action: 'LOGIN_FAILED',
                email,
                ipAddress,
                success: false,
                errorMessage: 'User not found'
              }
            });
            return null;
          }

          // Check if account is locked
          if (user.lockedUntil && user.lockedUntil > new Date()) {
            const minutesLeft = Math.ceil((user.lockedUntil.getTime() - Date.now()) / 60000);
            throw new Error(`Account locked. Try again in ${minutesLeft} minutes.`);
          }

          // Check if email is verified
          if (!user.emailVerified) {
            throw new Error("Please verify your email before signing in");
          }

          // Verify password
          const isValidPassword = await compare(credentials.password, user.password);

          if (!isValidPassword) {
            // Increment failed attempts
            const failedAttempts = user.failedLoginAttempts + 1;
            const isLocked = failedAttempts >= MAX_LOGIN_ATTEMPTS;

            await prisma.user.update({
              where: { id: user.id },
              data: {
                failedLoginAttempts: failedAttempts,
                lockedUntil: isLocked ? new Date(Date.now() + LOCKOUT_DURATION) : null
              }
            });

            // Log failed attempt
            await prisma.auditLog.create({
              data: {
                action: 'LOGIN_FAILED',
                userId: user.id,
                email,
                ipAddress,
                success: false,
                errorMessage: 'Invalid password',
                metadata: { failedAttempts }
              }
            });

            if (isLocked) {
              throw new Error("Too many failed attempts. Account locked for 30 minutes.");
            }

            return null;
          }

          // Success - reset failed attempts and update last login
          await prisma.user.update({
            where: { id: user.id },
            data: {
              failedLoginAttempts: 0,
              lockedUntil: null,
              lastLoginAt: new Date(),
              lastLoginIp: ipAddress
            }
          });

          // Log successful login
          await prisma.auditLog.create({
            data: {
              action: 'LOGIN_SUCCESS',
              userId: user.id,
              email,
              ipAddress,
              success: true
            }
          });

          return {
            id: user.id,
            email: user.email!,
            name: user.name || user.email!,
            role: user.role
          } as ExtendedUser;
        } catch (error) {
          if (error instanceof Error) {
            throw error;
          }
          throw new Error("Authentication failed");
        }
      }
    })
  ],
  secret: config.auth.secret,
  session: { 
    strategy: "jwt",
    maxAge: config.security.sessionMaxAge,
  },
  // Cookie security configuration for production
  cookies: {
    sessionToken: {
      name: `${config.environment.isProduction ? '__Secure-' : ''}next-auth.session-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: config.environment.isProduction
      }
    },
    callbackUrl: {
      name: `${config.environment.isProduction ? '__Secure-' : ''}next-auth.callback-url`,
      options: {
        sameSite: 'lax',
        path: '/',
        secure: config.environment.isProduction
      }
    },
    csrfToken: {
      name: `${config.environment.isProduction ? '__Secure-' : ''}next-auth.csrf-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: config.environment.isProduction
      }
    }
  },
  callbacks: {
    jwt: async ({ token, user }) => {
      if (user) {
        const extendedUser = user as ExtendedUser;
        token.id = extendedUser.id;
        token.email = extendedUser.email;
        token.name = extendedUser.name;
        token.role = extendedUser.role;
      }
      return token;
    },
    session: async ({ session, token }) => {
      if (session?.user && token) {
        // Add user ID and role to session
        session.user.id = token.id;
        session.user.role = token.role;
      }
      return session;
    },
  },
};