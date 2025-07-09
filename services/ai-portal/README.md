# AI Portal - RJLF Legal Services

The AI Portal is a professional landing page and gateway for Reichman Jorgensen Lehman & Feldberg LLP's AI services. It provides access to AI policies, best practices, and direct links to the firm's AI tools.

## Overview

The AI Portal serves as the entry point for RJLF's AI ecosystem, offering:

- **Professional Landing Page**: Branded interface with firm logo and styling
- **AI Security Policy**: Comprehensive policy documentation for AI usage
- **Best Practices Guide**: Guidelines for effective and safe AI utilization
- **Direct Access Links**: Quick access to Claude AI and Aletheia chat systems
- **Responsive Design**: Mobile-friendly interface with modern animations

## Technology Stack

- **Framework**: Next.js 15.3.4 with React 19
- **Language**: TypeScript 5.8.3
- **Styling**: Tailwind CSS 3.4.17
- **Deployment**: Static export with Docker containerization
- **Proxy**: NGINX for production serving

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client        │────▶│   NGINX Proxy   │────▶│   Next.js App   │
│   (Browser)     │     │   (Port 8085)   │     │   (Port 3000)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Features

### 1. Landing Page
- **Animated Interface**: Smooth transitions and floating particle effects
- **Branded Design**: RJLF logo with professional color scheme
- **Responsive Layout**: Optimized for desktop and mobile devices

### 2. Modal Components
- **AI Security Policy**: Detailed policy documentation in modal format
- **Best Practices Guide**: Interactive guidelines for AI usage
- **Keyboard Navigation**: ESC key support and focus management

### 3. External Integrations
- **Claude AI Access**: Direct link to Claude AI platform
- **Aletheia Integration**: Seamless connection to local Aletheia chat (`http://localhost:8080/chat`)

### 4. Deployment Features
- **Static Export**: Optimized for CDN deployment
- **GitHub Pages Support**: Configurable for GitHub Pages deployment
- **Docker Ready**: Containerized for easy deployment

## Installation & Setup

### Prerequisites
- Node.js 18+ and npm 9+
- Docker and Docker Compose (for containerized deployment)

### Local Development

1. **Navigate to AI Portal directory**:
   ```bash
   cd services/ai-portal
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Access the application**:
   - Local: http://localhost:3000
   - Via main stack: http://localhost:8085

### Docker Deployment

The AI Portal is automatically deployed as part of the main Aletheia stack:

```bash
# From project root
docker-compose up -d
```

The service will be available at http://localhost:8085

## Configuration

### Environment Variables

The AI Portal supports the following environment configurations:

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | `development` | Environment mode |
| `GITHUB_PAGES` | `false` | Enable GitHub Pages deployment mode |
| `PORT` | `3000` | Internal port for the Next.js application |

### Next.js Configuration

The application is configured for static export with conditional GitHub Pages support:

- **Static Export**: Generates optimized static files
- **Image Optimization**: Disabled for static export compatibility
- **Base Path**: Configurable for subdirectory deployment
- **Trailing Slashes**: Enabled for better hosting compatibility

### GitHub Pages Deployment

For GitHub Pages deployment, set the following environment variables:

```bash
NODE_ENV=production
GITHUB_PAGES=true
```

This will configure the application with the correct base path (`/landing_page_RJLF`).

## Customization

### Branding
- **Logo**: Replace `/public/rjlf_logo.png` with your firm's logo
- **Colors**: Modify Tailwind configuration for custom color schemes
- **Content**: Update modal components for firm-specific policies

### Links
- **External Links**: Update `page.tsx` to point to your preferred AI platforms
- **Internal Links**: Modify Aletheia links to match your deployment URLs

## Docker Services

The AI Portal consists of two Docker services:

### 1. ai-portal (Application)
- **Image**: Built from local Dockerfile
- **Port**: Internal port 3000
- **Function**: Serves the Next.js static export

### 2. ai-portal-nginx (Proxy)
- **Image**: nginx:alpine
- **Port**: External port 8085
- **Function**: Proxies requests to the Next.js application

## File Structure

```
services/ai-portal/
├── app/                          # Next.js App Router
│   ├── components/              # React components
│   │   ├── BestPracticesModal.tsx
│   │   ├── PolicyModal.tsx
│   │   └── ErrorBoundary.tsx
│   ├── globals.css             # Global styles
│   ├── layout.tsx              # Root layout
│   └── page.tsx                # Main landing page
├── public/                      # Static assets
│   ├── rjlf_logo.png           # Firm logo
│   └── favicon.svg             # Site icon
├── Dockerfile                   # Container configuration
├── nginx.conf                   # NGINX proxy configuration
├── next.config.js              # Next.js configuration
├── package.json                # Dependencies and scripts
├── tailwind.config.js          # Tailwind CSS configuration
└── tsconfig.json               # TypeScript configuration
```

## Development Commands

```bash
# Development server
npm run dev

# Production build
npm run build

# Production preview
npm run start
```

## Integration with Aletheia

The AI Portal is integrated into the main Aletheia ecosystem:

1. **Service Discovery**: Accessible via main navigation at http://localhost:8085
2. **Cross-Links**: Direct links to Aletheia chat interface
3. **Shared Network**: Connected to the frontend Docker network
4. **Unified Access**: Part of the multi-app architecture

## Troubleshooting

### Common Issues

1. **Port 8085 not accessible**:
   - Verify Docker services are running: `docker-compose ps`
   - Check NGINX proxy configuration
   - Ensure no port conflicts

2. **Static assets not loading**:
   - Rebuild the Docker image: `docker-compose build ai-portal`
   - Check Next.js build output for errors

3. **Links not working**:
   - Verify target services are running (Aletheia chat)
   - Check network connectivity between services

### Logs

```bash
# View AI Portal logs
docker-compose logs ai-portal

# View NGINX proxy logs
docker-compose logs ai-portal-nginx
```

## Security Considerations

- **Static Export**: No server-side code execution reduces attack surface
- **Non-root User**: Docker container runs as non-privileged user
- **NGINX Proxy**: Provides additional security layer
- **External Links**: Uses secure HTTPS connections where possible

## Performance

- **Static Generation**: Pre-built static files for fast loading
- **CDN Ready**: Optimized for content delivery network deployment
- **Minimal Dependencies**: Lightweight React application
- **Image Optimization**: Compressed assets with blur placeholders

## Contributing

When modifying the AI Portal:

1. **Test Locally**: Always test changes in development mode
2. **Build Verification**: Ensure production build succeeds
3. **Docker Testing**: Test the complete Docker deployment
4. **Cross-browser Testing**: Verify compatibility across browsers
5. **Responsive Testing**: Check mobile and desktop layouts

## License

This AI Portal is part of the Aletheia-v0.1 project and follows the same MIT license terms.