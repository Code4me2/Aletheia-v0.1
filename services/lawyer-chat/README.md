# Lawyer-Chat

A comprehensive AI-powered legal assistant interface integrated into the Aletheia-v0.1 platform, providing secure chat functionality with n8n webhook integration, document processing, and advanced legal research capabilities.

## 🎯 Recent Updates (August 2025)

### New Document Context Feature
- **DocumentCabinet**: Court opinion selection panel accessible via button in top-right corner
- **Integration with Court Processor**: Fetches real court opinions from database
- **Judges Supported**: Gilstrap and Albright (expandable)
- **Document Selection**: Click to select multiple documents for chat context

### UI Refactoring
The application has been significantly refactored for better maintainability:
- Main page reduced from 900+ lines to modular components
- New component structure in `src/components/`
- Custom hooks for state and API management
- API routes versioned under `/api/v1/`

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local development)
- PostgreSQL database (provided by data-compose)
- n8n instance running (provided by data-compose)
- (Optional) SMTP server for email notifications

### 1. Navigate to the service directory
```bash
cd services/lawyer-chat
```

### 2. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Build and start the service
```bash
# From data-compose root directory
docker-compose build lawyer-chat
docker-compose up -d
```

**Important NODE_ENV Configuration:**
- NODE_ENV is now controlled via docker-compose.yml (not hardcoded in Dockerfile)
- Development: Uses `NODE_ENV=development` (default) - cookies work over HTTP
- Production: Must set `NODE_ENV=production` - requires HTTPS for secure cookies
- Change in .env file or docker-compose.yml takes effect after container restart

### 4. Access the application
- **Lawyer-Chat Interface**: http://localhost:8080/chat
- **Health Check**: http://localhost:8080/chat/api/csrf

### 5. Create demo users

For quick testing, create pre-verified demo users:

```bash
# See DEMO_CREDENTIALS_SETUP.md for the simplest method
docker exec aletheia-db-1 psql -U your_db_user -d lawyerchat << 'EOF'
INSERT INTO "User" (id, email, name, password, role, "emailVerified", "createdAt", "updatedAt", "failedLoginAttempts")
VALUES 
  ('demo-user-001', 'demo@reichmanjorgensen.com', 'Demo User', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'user', NOW(), NOW(), NOW(), 0),
  ('admin-user-001', 'admin@reichmanjorgensen.com', 'Admin User', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin', NOW(), NOW(), NOW(), 0);
EOF
```

**Demo Credentials:**
- Demo: `demo@reichmanjorgensen.com` / `password`
- Admin: `admin@reichmanjorgensen.com` / `password`

**Note:** The `npm run create-admin` script requires tsx which is not available in production containers. See [DEMO_CREDENTIALS_SETUP.md](./DEMO_CREDENTIALS_SETUP.md) for details and alternative methods.

### 6. Configure n8n webhook
1. Access n8n at http://localhost:8080/n8n/
2. Verify webhook workflow is active
3. Check webhook ID matches: `c188c31c-1c45-4118-9ece-5b6057ab5177`

## Overview

Lawyer-Chat is a Next.js-based web application designed for legal professionals at Reichman Jorgensen Lehman & Feldberg LLP (RJLF). Built with Node.js 20 Alpine Docker images for enhanced security and performance. It provides:

- **Enterprise-grade authentication** with email domain validation and secure registration flows
- **AI-powered legal assistant** with real-time streaming responses via n8n/DeepSeek integration
- **Advanced security features** including CSRF protection, rate limiting, and comprehensive audit logging
- **Professional tools** for document export, citation management, and legal analytics visualization
- **Modern user experience** with dark mode, responsive design, and persistent chat history

## Key Features

### 🔐 Enterprise Authentication
- Email domain validation (@reichmanjorgensen.com)
- Secure registration with email verification
- Password reset flows with token expiration
- Account lockout after failed attempts
- Comprehensive audit logging
- Role-based access control

### 💬 AI-Powered Legal Chat
- Real-time streaming responses with SSE
- DeepSeek R1 integration via n8n webhooks
- Markdown rendering with syntax highlighting
- Code block support with language detection
- LaTeX math rendering
- Auto-save during streaming

### 📄 Document Management
- PDF export of conversations
- Text export with formatting
- Chat history persistence
- Automatic title generation
- Message search capability

### 🎨 Professional Interface
- Dark/light theme support
- Responsive design for all devices
- Citation panel for legal references
- Mock analytics dashboard
- Keyboard shortcuts
- Accessibility features

### 🔒 Security Features
- CSRF token protection
- Rate limiting (Edge + Redis)
- Session encryption
- Field-level encryption (AES-256-GCM)
- Secure cookie handling
- Input validation & sanitization
- XSS prevention
- Account lockout mechanism
- Comprehensive audit logging
- User enumeration protection
- Email failure resilience
- Security headers (CSP, HSTS, etc.)

📖 **See [SECURITY_FEATURES.md](./SECURITY_FEATURES.md) for complete security documentation**

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Lawyer-Chat Application                    │
├─────────────────────────────────────────────────────────────────┤
│                          Frontend Layer                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │   Next.js   │  │    React     │  │   Tailwind CSS 4.0     │ │
│  │  App Router │  │  Components  │  │   (Beta Features)      │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                          API Layer                                │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  NextAuth   │  │   Chat API   │  │    Admin API           │ │
│  │   Routes    │  │  (SSE/JSON)  │  │   (Protected)          │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      Security Layer                               │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │    CSRF     │  │Rate Limiting │  │   Audit Logging        │ │
│  │ Protection  │  │  (Dual Mode) │  │   (PostgreSQL)         │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      Data Layer                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Prisma ORM │  │  PostgreSQL  │  │     Redis              │ │
│  │  (Type-safe)│  │  (lawyerchat)│  │   (Optional)           │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    External Integration                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           n8n Webhook (c188c31c-1c45-4118-9ece-5b6057ab5177)│ │
│  │                    DeepSeek R1 AI Model                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
services/lawyer-chat/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── api/               # API routes
│   │   │   ├── auth/         # Authentication endpoints
│   │   │   │   ├── register/
│   │   │   │   ├── verify-email/
│   │   │   │   ├── forgot-password/
│   │   │   │   └── reset-password/
│   │   │   ├── chat/         # Chat streaming endpoint
│   │   │   ├── chats/        # Chat history management
│   │   │   ├── csrf/         # CSRF token generation
│   │   │   └── admin/        # Admin endpoints
│   │   ├── auth/             # Auth pages
│   │   │   ├── signin/
│   │   │   ├── register/
│   │   │   └── forgot-password/
│   │   ├── admin/            # Admin dashboard
│   │   ├── layout.tsx        # Root layout
│   │   └── page.tsx          # Main chat interface
│   ├── components/           # React components
│   │   ├── AuthGuard.tsx    # Authentication wrapper
│   │   ├── CitationPanel.tsx # Legal citations view
│   │   ├── DarkModeToggle.tsx # Theme switcher
│   │   ├── DownloadButton.tsx # Export functionality
│   │   ├── ErrorBoundary.tsx  # Error handling
│   │   ├── SafeMarkdown.tsx   # Secure markdown rendering
│   │   └── TaskBar.tsx        # Chat history sidebar
│   ├── hooks/                # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useChat.ts
│   │   └── useDarkMode.ts
│   ├── lib/                  # Core libraries
│   │   ├── auth.ts          # NextAuth configuration
│   │   ├── config.ts        # Environment config
│   │   ├── prisma.ts        # Database client
│   │   └── rateLimiter.ts   # Rate limiting logic
│   ├── store/               # Zustand state stores
│   │   ├── csrf.ts         # CSRF token management
│   │   └── sidebar.ts      # UI state
│   ├── types/              # TypeScript definitions
│   │   ├── next-auth.d.ts
│   │   └── api.ts
│   └── utils/              # Utility functions
│       ├── api.ts         # API client wrapper
│       ├── auth.ts        # Auth helpers
│       ├── csrf.ts        # CSRF utilities
│       ├── email.ts       # Email sending
│       ├── logger.ts      # Logging utility
│       ├── pdfGenerator.ts # PDF export
│       └── validation.ts   # Input validation
├── prisma/
│   ├── schema.prisma      # Database schema
│   └── seed.ts           # Database seeding
├── public/               # Static assets
│   └── logo.png         # Application logo
├── scripts/             # Utility scripts
│   ├── create-admin.ts  # Admin user creation
│   └── docker-entrypoint.sh # Container startup
├── e2e/                # Playwright E2E tests
│   ├── auth.spec.ts
│   ├── chat.spec.ts
│   ├── admin.spec.ts
│   ├── export.spec.ts
│   └── ui-ux.spec.ts
├── .env.example        # Environment template
├── Dockerfile          # Multi-stage build
├── next.config.ts      # Next.js configuration
├── tailwind.config.ts  # Tailwind CSS config
├── tsconfig.json       # TypeScript config
├── jest.config.js      # Jest testing config
├── playwright.config.ts # E2E testing config
└── package.json        # Dependencies
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Core Configuration
NODE_ENV=production
NEXTAUTH_SECRET=your-secret-key-min-32-chars  # Generate with: openssl rand -base64 32
NEXTAUTH_URL=http://localhost:8080/chat

# Database
DATABASE_URL=postgresql://user:pass@db:5432/lawyerchat

# n8n Integration
N8N_WEBHOOK_URL=http://n8n:5678/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177
N8N_API_KEY=your-api-key         # Optional: for authenticated webhooks
N8N_API_SECRET=your-api-secret   # Optional: for authenticated webhooks

# Email Configuration (Required for production)
EMAIL_MODE=production  # console | test | production
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=noreply@reichmanjorgensen.com
SMTP_PASS=your-smtp-password
SMTP_FROM="Aletheia Legal <noreply@reichmanjorgensen.com>"

# Security Configuration
ALLOWED_EMAIL_DOMAINS=@reichmanjorgensen.com
SESSION_MAX_AGE=28800  # 8 hours in seconds
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=1800000  # 30 minutes in ms
PASSWORD_MIN_LENGTH=8
TOKEN_EXPIRY_HOURS=24
RESET_TOKEN_EXPIRY_HOURS=1

# Redis (Optional - for production rate limiting)
REDIS_URL=redis://redis:6379/0

# Logging
LOG_LEVEL=info  # debug | info | warn | error
```

### Authentication Configuration

#### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

#### Security Features
- Account lockout after 5 failed attempts
- 30-minute lockout duration
- IP address logging for all auth events
- Comprehensive audit trail
- Email verification required

### Integration Configuration

#### n8n Webhook
The application integrates with n8n via webhook. Request format:
```json
{
  "action": "chat",
  "message": "User's question",
  "sessionId": "user-email",
  "sessionKey": "chat-id",
  "userId": "user-email"
}
```

#### CSRF Protection
- Tokens generated per session
- Required header: `X-CSRF-Token`
- Exempt paths: `/api/csrf`, `/api/auth/*`, `/api/health`

## Development

### Local Development

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with local settings
   ```

3. **Generate Prisma client**
   ```bash
   npx prisma generate
   ```

4. **Run database migrations**
   ```bash
   npx prisma migrate dev
   ```

5. **Start development server**
   ```bash
   npm run dev
   ```
   Access at http://localhost:8080/chat (via nginx proxy)

### Testing

#### Unit Tests
```bash
npm test                # Run all tests
npm run test:watch     # Watch mode
npm run test:coverage  # Coverage report
```

#### E2E Tests
```bash
npm run test:e2e       # Run Playwright tests
npm run test:e2e:ui    # Interactive UI mode
npm run test:e2e:debug # Debug mode
```

### Building for Production

#### Docker Build
```bash
docker build -t lawyer-chat .
```

#### Next.js Build
```bash
npm run build
npm start
```

## Advanced Features

### Chat System
- **Streaming Responses**: Real-time SSE for AI responses
- **Markdown Support**: Full CommonMark spec with extensions
- **Code Highlighting**: Syntax highlighting for 20+ languages
- **Math Rendering**: LaTeX support for mathematical expressions
- **Auto-save**: Messages saved during streaming

### Export Features
- **PDF Export**: Full conversation with formatting
- **Text Export**: Plain text with timestamps
- **Custom Styling**: Professional document appearance
- **Metadata**: Include chat title and timestamps

### Dark Mode
- **System Detection**: Follows OS preference
- **Manual Override**: User toggle persisted
- **Smooth Transitions**: CSS-based animations
- **Complete Coverage**: All UI elements themed

### Analytics (Mock)
- **Case Predictions**: Outcome probability
- **Relevant Statutes**: Legal references
- **Risk Assessment**: Case risk factors
- **Time Estimates**: Processing duration
- **Confidence Scores**: Prediction reliability

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database status
docker exec -it postgres-container pg_isready

# Verify connection string
docker exec lawyer-chat npx prisma db pull
```

#### CSRF Token Errors
- Clear browser cookies
- Check middleware configuration
- Verify CSRF endpoint accessibility

#### Email Not Sending
```bash
# Test email configuration
docker exec lawyer-chat npm run test-email

# Check logs
docker logs lawyer-chat | grep -i email
```

#### Chat Not Responding
```bash
# Verify n8n webhook
curl -X POST http://localhost:8080/chat/api/chat \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: your-token" \
  -d '{"message": "Test"}'

# Check n8n workflow status
# Access n8n UI and verify workflow is active
```

### Debug Mode

Enable detailed logging:
```bash
LOG_LEVEL=debug npm run dev
```

### Health Checks

- **Application**: GET `/chat/api/csrf`
- **Database**: `npx prisma db pull`
- **n8n Integration**: Check workflow execution logs

## Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Standards
- TypeScript strict mode enabled
- ESLint configuration enforced
- Prettier formatting required
- 90%+ test coverage target

### Commit Guidelines
- Use conventional commits
- Include tests for new features
- Update documentation
- Run full test suite before PR

## License

This project is part of the Aletheia-v0.1 platform. See the main project LICENSE file for details.

## Acknowledgments

- Built with [Next.js](https://nextjs.org/) and [React](https://reactjs.org/)
- Authentication by [NextAuth.js](https://next-auth.js.org/)
- Database ORM by [Prisma](https://www.prisma.io/)
- UI components styled with [Tailwind CSS](https://tailwindcss.com/)
- AI integration through [n8n](https://n8n.io/) and [DeepSeek](https://www.deepseek.com/)

## Technical Details for Developers

### New Component Structure (August 2025)

#### Components
- **DocumentCabinet** (`src/components/DocumentCabinet.tsx`)
  - Main entry point for document selection
  - Sliding panel UI with toggle button
  - Manages selected documents state
  
- **DocumentSelector** (`src/components/document-selector/DocumentSelector.tsx`)
  - Document list and filtering interface
  - Handles API calls to court-processor
  
- **ChatWithDocuments** (`src/components/chat/ChatWithDocuments.tsx`)
  - Alternative chat interface with document context
  - Standalone component for document-aware conversations

#### Custom Hooks
- **useChatAPI** (`src/hooks/useChatAPI.ts`): Centralized API logic
- **useChatState** (`src/hooks/useChatState.ts`): State management
- **useDocumentSelection** (`src/hooks/useDocumentSelection.ts`): Document selection logic

#### API Integration
- **court-api.ts** (`src/lib/court-api.ts`)
  - Client for court-processor simplified API
  - Endpoints: `/search`, `/text/{id}`, `/documents/{id}`, `/bulk/judge/{name}`
  - Base URL: `http://court-processor:8104` (internal Docker network)

#### Utilities
- **utils.ts** (`src/lib/utils.ts`)
  - Contains `cn()` function for className merging (using clsx + tailwind-merge)
  - Required dependency: `clsx` and `tailwind-merge`

### Court Processor Integration

The DocumentCabinet connects to the court-processor service via its simplified API:

```javascript
// Default configuration in court-api.ts
baseUrl: process.env.COURT_API_BASE_URL || 'http://court-processor:8104'
clientUrl: process.env.NEXT_PUBLIC_COURT_API_URL || 'http://localhost:8104'
```

**Important**: The court-processor must have its `simplified_api.py` running on port 8104.

### Build Configuration

The following environment variables must be set at BUILD TIME for Next.js:
- `NEXT_PUBLIC_ENABLE_DOCUMENT_SELECTION`: Enable/disable the feature
- `NEXT_PUBLIC_COURT_API_URL`: Public URL for court API
- `COURT_API_BASE_URL`: Internal Docker URL for court API

These are configured as build args in `docker-compose.yml`.

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review [closed issues](https://github.com/Code4me2/Aletheia-v0.1/issues?q=is%3Aissue+is%3Aclosed)
- Contact the Aletheia development team