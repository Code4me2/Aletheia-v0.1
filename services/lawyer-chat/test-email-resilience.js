// Test script to verify email failure resilience
const fetch = require('node-fetch');

async function testEmailResilience() {
  const baseUrl = 'http://localhost:3001/chat/api/auth/register';
  
  // Test data
  const testUser = {
    email: `test.resilience.${Date.now()}@reichmanjorgensen.com`,
    password: 'TestPass123!',
    confirmPassword: 'TestPass123!',
    name: 'Email Resilience Test'
  };

  console.log('Testing email failure resilience...');
  console.log('Registering user:', testUser.email);

  try {
    const response = await fetch(baseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(testUser)
    });

    const data = await response.json();
    
    console.log('Response status:', response.status);
    console.log('Response data:', JSON.stringify(data, null, 2));

    if (response.status === 201) {
      console.log('\n✅ SUCCESS: Registration completed');
      
      if (data.emailSent === false) {
        console.log('✅ Email sending failed but user was created');
        console.log('✅ This confirms the email failure resilience is working!');
      } else {
        console.log('ℹ️  Email was sent successfully');
      }
    } else {
      console.log('\n❌ ERROR: Registration failed');
    }

  } catch (error) {
    console.error('Error testing registration:', error);
  }
}

// Run the test
testEmailResilience();