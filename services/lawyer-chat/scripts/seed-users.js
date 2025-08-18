const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function main() {
  console.log('Seeding database...');

  try {
    // Create demo user
    const demoPassword = await bcrypt.hash('demo123', 12);
    
    const demoUser = await prisma.user.upsert({
      where: { email: 'demo@reichmanjorgensen.com' },
      update: {},
      create: {
        email: 'demo@reichmanjorgensen.com',
        name: 'Demo User',
        password: demoPassword,
        emailVerified: new Date(),
        role: 'USER',
      },
    });

    console.log('Created demo user:', demoUser.email);

    // Create admin user
    const adminPassword = await bcrypt.hash('admin123', 12);
    
    const adminUser = await prisma.user.upsert({
      where: { email: 'admin@reichmanjorgensen.com' },
      update: {},
      create: {
        email: 'admin@reichmanjorgensen.com',
        name: 'Admin User',
        password: adminPassword,
        emailVerified: new Date(),
        role: 'ADMIN',
      },
    });

    console.log('Created admin user:', adminUser.email);
    console.log('\nUsers created successfully!');
    console.log('Demo user: demo@reichmanjorgensen.com / demo123');
    console.log('Admin user: admin@reichmanjorgensen.com / admin123');
  } catch (error) {
    console.error('Error seeding database:', error);
  }
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error(e);
    await prisma.$disconnect();
    process.exit(1);
  });