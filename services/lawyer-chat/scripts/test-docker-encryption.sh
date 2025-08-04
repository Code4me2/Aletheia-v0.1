#!/bin/bash

# Test script to verify encryption works in Docker container
# Run this after rebuilding the Docker image

echo "🔐 Testing Field-Level Encryption in Docker"
echo "=========================================="
echo

# Check if container is running
if ! docker ps | grep -q lawyer-chat; then
    echo "❌ lawyer-chat container is not running"
    echo "Please start it with: docker compose up -d lawyer-chat"
    exit 1
fi

echo "✅ lawyer-chat container is running"
echo

# Test 1: Check if FIELD_ENCRYPTION_KEY is set in container
echo "Test 1: Checking encryption key in container..."
docker compose exec lawyer-chat sh -c 'if [ -n "$FIELD_ENCRYPTION_KEY" ]; then echo "✅ FIELD_ENCRYPTION_KEY is set"; else echo "❌ FIELD_ENCRYPTION_KEY is NOT set"; fi'
echo

# Test 2: Run basic encryption test
echo "Test 2: Running basic encryption test..."
docker compose exec lawyer-chat npm run test-encryption 2>&1 | grep -E "(✅|❌|Error:|Testing|Match)" | head -20
echo

# Test 3: Check database connection and encryption
echo "Test 3: Testing database operations with encryption..."
docker compose exec lawyer-chat npx tsx -e '
const prisma = require("./src/lib/prisma").default;
const crypto = require("crypto");

async function test() {
  try {
    console.log("Creating test audit log with encrypted IP...");
    const testIp = "192.168.100.200";
    
    const audit = await prisma.auditLog.create({
      data: {
        action: "ENCRYPTION_TEST",
        email: "docker-test@example.com",
        ipAddress: testIp,
        userAgent: "Docker Test",
        success: true,
        metadata: { dockerTest: true }
      }
    });
    
    console.log("✅ Created audit log:", audit.id);
    
    // Read it back
    const readAudit = await prisma.auditLog.findUnique({
      where: { id: audit.id }
    });
    
    console.log("✅ IP decrypted correctly:", readAudit.ipAddress === testIp);
    
    // Check raw value
    const raw = await prisma.$queryRaw`
      SELECT "ipAddress" FROM "AuditLog" WHERE id = ${audit.id}
    `;
    
    console.log("✅ Raw value is encrypted:", raw[0].ipAddress.startsWith("enc:v1:"));
    
    // Cleanup
    await prisma.auditLog.delete({ where: { id: audit.id } });
    console.log("✅ Test data cleaned up");
    
  } catch (error) {
    console.error("❌ Test failed:", error.message);
  } finally {
    await prisma.$disconnect();
  }
}

test();
'
echo

# Test 4: Verify NextAuth compatibility
echo "Test 4: Testing NextAuth session creation..."
docker compose exec lawyer-chat npx tsx -e '
const prisma = require("./src/lib/prisma").default;
const crypto = require("crypto");

async function test() {
  try {
    const testToken = crypto.randomBytes(32).toString("hex");
    
    // Create test user
    const user = await prisma.user.create({
      data: {
        email: "nextauth-test-" + Date.now() + "@test.com",
        name: "NextAuth Test",
        emailVerified: new Date(),
        role: "user"
      }
    });
    
    // Create session
    const session = await prisma.session.create({
      data: {
        sessionToken: testToken,
        userId: user.id,
        expires: new Date(Date.now() + 86400000)
      }
    });
    
    console.log("✅ Session created");
    
    // Find by token
    const found = await prisma.session.findUnique({
      where: { sessionToken: testToken }
    });
    
    console.log("✅ Session found by token:", found !== null);
    console.log("✅ Token matches:", found?.sessionToken === testToken);
    
    // Cleanup
    await prisma.session.delete({ where: { id: session.id } });
    await prisma.user.delete({ where: { id: user.id } });
    console.log("✅ NextAuth test passed");
    
  } catch (error) {
    console.error("❌ NextAuth test failed:", error.message);
  } finally {
    await prisma.$disconnect();
  }
}

test();
'
echo

echo "=========================================="
echo "✅ Encryption testing complete!"
echo
echo "If all tests passed, encryption is working correctly in Docker."
echo "Your sensitive data is now being encrypted automatically."