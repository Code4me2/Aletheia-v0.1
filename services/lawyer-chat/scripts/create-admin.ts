#!/usr/bin/env node

/**
 * Script to create an admin user
 * Usage: npm run create-admin -- --email admin@reichmanjorgensen.com --password YourSecurePassword123!
 */

import bcrypt from 'bcryptjs';
import { PrismaClient } from '@prisma/client';
import dotenv from 'dotenv';
import { parseArgs } from 'util';

// Load environment variables
dotenv.config({ path: '.env.local' });

const prisma = new PrismaClient();

async function createAdmin() {
  try {
    // Parse command line arguments
    const { values } = parseArgs({
      options: {
        email: {
          type: 'string',
          short: 'e',
        },
        password: {
          type: 'string',
          short: 'p',
        },
        name: {
          type: 'string',
          short: 'n',
        }
      }
    });

    const email = values.email as string;
    const password = values.password as string;
    const name = values.name as string || 'Admin User';

    if (!email || !password) {
      console.error('❌ Email and password are required');
      console.log('Usage: npm run create-admin -- --email admin@reichmanjorgensen.com --password YourSecurePassword123!');
      process.exit(1);
    }

    // Validate email domain
    if (!email.endsWith('@reichmanjorgensen.com')) {
      console.error('❌ Email must be a @reichmanjorgensen.com address');
      process.exit(1);
    }

    // Check if user already exists
    const existingUser = await prisma.user.findUnique({
      where: { email: email.toLowerCase() }
    });

    if (existingUser) {
      console.error('❌ User with this email already exists');
      
      // If user exists but is not admin, offer to upgrade
      if (existingUser.role !== 'admin') {
        console.log('This user is not an admin. Upgrading to admin role...');
        await prisma.user.update({
          where: { id: existingUser.id },
          data: { role: 'admin' }
        });
        console.log('✅ User upgraded to admin successfully!');
      } else {
        console.log('ℹ️  User is already an admin');
      }
      process.exit(0);
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 12);

    // Create admin user
    const user = await prisma.user.create({
      data: {
        email: email.toLowerCase(),
        name,
        password: hashedPassword,
        role: 'admin',
        emailVerified: new Date() // Auto-verify admin accounts
      }
    });

    console.log('✅ Admin user created successfully!');
    console.log('📧 Email:', user.email);
    console.log('👤 Name:', user.name);
    console.log('🔐 Role:', user.role);
    console.log('\nYou can now sign in with these credentials.');

  } catch (error) {
    console.error('❌ Error creating admin user:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

createAdmin();