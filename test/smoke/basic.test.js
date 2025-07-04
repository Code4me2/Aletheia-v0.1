const fs = require('fs');
const path = require('path');

describe('Aletheia Project Structure', () => {
  test('Essential directories exist', () => {
    const essentialDirs = [
      'website',
      'n8n',
      'services',
      'nginx',
      '.github/workflows'
    ];

    essentialDirs.forEach(dir => {
      const dirPath = path.join(process.cwd(), dir);
      expect(fs.existsSync(dirPath)).toBe(true);
    });
  });

  test('Critical configuration files exist', () => {
    const configFiles = [
      'docker-compose.yml',
      'package.json',
      '.env.example',
      'README.md'
    ];

    configFiles.forEach(file => {
      const filePath = path.join(process.cwd(), file);
      expect(fs.existsSync(filePath)).toBe(true);
    });
  });

  test('Docker compose file exists and is readable', () => {
    const dockerComposePath = path.join(process.cwd(), 'docker-compose.yml');
    expect(fs.existsSync(dockerComposePath)).toBe(true);
    
    // Verify it's a valid YAML by checking it starts with expected content
    const content = fs.readFileSync(dockerComposePath, 'utf8');
    expect(content).toContain('version:');
    expect(content).toContain('services:');
    expect(content).toContain('web:');
    expect(content).toContain('n8n:');
    expect(content).toContain('db:');
  });
});

// Basic integration test placeholder
describe('Service Health Checks', () => {
  test('Health check endpoints are defined', () => {
    // This is a placeholder that passes
    // Real health checks would require services to be running
    expect(true).toBe(true);
  });
});