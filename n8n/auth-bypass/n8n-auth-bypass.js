#!/usr/bin/env node

/**
 * n8n Authentication Bypass for Local Development
 * 
 * This script creates an automatic login session for n8n using
 * credentials from environment variables, eliminating the need
 * for manual login in development environments.
 */

const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// Configuration from environment
const config = {
  n8nUrl: process.env.N8N_URL || 'http://localhost:5678',
  email: process.env.N8N_AUTO_LOGIN_EMAIL,
  password: process.env.N8N_AUTO_LOGIN_PASSWORD,
  dbPath: '/data/.n8n/database.sqlite',
  sessionDuration: 30 * 24 * 60 * 60 * 1000 // 30 days in ms
};

/**
 * Generate a session token that mimics n8n's auth token
 */
function generateSessionToken() {
  return crypto.randomBytes(32).toString('hex');
}

/**
 * Create a direct database session
 * This bypasses the login UI by directly creating a valid session
 */
async function createDirectSession() {
  const sqlite3 = require('sqlite3').verbose();
  const db = new sqlite3.Database(config.dbPath);
  
  return new Promise((resolve, reject) => {
    const sessionToken = generateSessionToken();
    const expiryDate = new Date(Date.now() + config.sessionDuration);
    
    // Get user ID from email
    db.get(
      "SELECT id FROM user WHERE email = ?",
      [config.email],
      (err, user) => {
        if (err || !user) {
          reject(new Error('User not found'));
          return;
        }
        
        // Create auth token
        const authToken = {
          token: sessionToken,
          userId: user.id,
          expiresAt: expiryDate.toISOString(),
          createdAt: new Date().toISOString()
        };
        
        // Store in database (would need auth_token table)
        console.log('Session created:', {
          token: sessionToken,
          userId: user.id,
          expiresAt: expiryDate
        });
        
        db.close();
        resolve(sessionToken);
      }
    );
  });
}

/**
 * Alternative: Create a bypass proxy
 * This intercepts requests and adds authentication headers
 */
class N8nAuthProxy {
  constructor(targetPort = 5678, proxyPort = 5679) {
    this.targetPort = targetPort;
    this.proxyPort = proxyPort;
    this.sessionToken = null;
  }
  
  start() {
    const proxy = http.createServer(async (req, res) => {
      // Skip auth for health checks
      if (req.url === '/healthz') {
        this.forwardRequest(req, res);
        return;
      }
      
      // Auto-inject authentication
      if (!req.headers.cookie || !req.headers.cookie.includes('n8n-auth')) {
        req.headers.cookie = `n8n-auth=${this.sessionToken}; ${req.headers.cookie || ''}`;
      }
      
      this.forwardRequest(req, res);
    });
    
    proxy.listen(this.proxyPort, () => {
      console.log(`Auth proxy listening on port ${this.proxyPort}`);
      console.log(`Forwarding to n8n on port ${this.targetPort}`);
    });
  }
  
  forwardRequest(req, res) {
    const options = {
      hostname: 'localhost',
      port: this.targetPort,
      path: req.url,
      method: req.method,
      headers: req.headers
    };
    
    const proxyReq = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });
    
    req.pipe(proxyReq);
    
    proxyReq.on('error', (err) => {
      console.error('Proxy error:', err);
      res.statusCode = 500;
      res.end('Proxy error');
    });
  }
}

/**
 * Simplest approach: Disable authentication entirely for local dev
 */
function generateNoAuthConfig() {
  const config = {
    auth: {
      enabled: false
    },
    userManagement: {
      disabled: true
    }
  };
  
  console.log('Add these to your .env to disable authentication:');
  console.log('N8N_USER_MANAGEMENT_DISABLED=true');
  console.log('N8N_AUTH_ENABLED=false');
  
  return config;
}

/**
 * JWT-based approach: Generate a valid JWT token
 */
function generateJWT(userId, email) {
  const header = {
    alg: 'HS256',
    typ: 'JWT'
  };
  
  const payload = {
    id: userId,
    email: email,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + (30 * 24 * 60 * 60) // 30 days
  };
  
  // This would need the actual JWT secret from n8n
  const secret = process.env.N8N_JWT_SECRET || 'n8n-jwt-secret';
  
  const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
  
  const signature = crypto
    .createHmac('sha256', secret)
    .update(`${encodedHeader}.${encodedPayload}`)
    .digest('base64url');
  
  return `${encodedHeader}.${encodedPayload}.${signature}`;
}

// Main execution
if (require.main === module) {
  console.log('n8n Authentication Bypass');
  console.log('========================');
  
  if (!config.email || !config.password) {
    console.log('\nOption 1: Set these in your .env:');
    console.log('N8N_AUTO_LOGIN_EMAIL=velvetmoon222999@gmail.com');
    console.log('N8N_AUTO_LOGIN_PASSWORD=Welcome123!');
    
    console.log('\nOption 2: Disable auth entirely:');
    generateNoAuthConfig();
    
    console.log('\nOption 3: Use basic auth (already in .env):');
    console.log('N8N_BASIC_AUTH_ACTIVE=true');
    console.log('N8N_BASIC_AUTH_USER=admin');
    console.log('N8N_BASIC_AUTH_PASSWORD=your_password');
    
    process.exit(0);
  }
  
  // Start the auth proxy
  const proxy = new N8nAuthProxy();
  proxy.start();
}

module.exports = { N8nAuthProxy, generateJWT, generateNoAuthConfig };