# Aletheia Quick Start Guide

Get Aletheia running in 5 minutes or less.

## Prerequisites

- Docker and docker-compose installed
- 4GB RAM available
- Ports 8080, 5678, 8085 available

## Setup (First Time Only)

### 1. Clone the repository
```bash
git clone [repository-url]
cd aletheia
```

### 2. Create your configuration
```bash
cp .env.required .env
```

### 3. Edit .env file
Open `.env` and set these 3 required values:
```env
DB_PASSWORD=your_secure_password_here
N8N_ENCRYPTION_KEY=any_random_32_character_string
NEXTAUTH_SECRET=any_random_64_character_string
```

To generate secure random strings:
```bash
# For N8N_ENCRYPTION_KEY (32+ chars)
openssl rand -base64 32

# For NEXTAUTH_SECRET (64 chars)
openssl rand -base64 48
```

## Daily Usage

### Start everything
```bash
./dev up
```

### Access the services
- **Main App**: http://localhost:8080
- **n8n Workflows**: http://localhost:8080/n8n
- **Lawyer Chat**: http://localhost:8080/chat
- **AI Portal**: http://localhost:8085

### View logs
```bash
./dev logs          # All services
./dev logs n8n      # Specific service
```

### Stop everything
```bash
./dev down
```

## Common Tasks

### Check service status
```bash
./dev status
```

### Restart a service
```bash
./dev restart lawyer-chat
```

### Access database
```bash
./dev shell db
```

### Clean everything (WARNING: Deletes data)
```bash
./dev clean
```

## Troubleshooting

### Services won't start
- Check `.env` has all 3 required variables set
- Ensure ports aren't already in use: `netstat -an | grep 8080`
- Check Docker is running: `docker ps`

### n8n workflows missing
- Workflows auto-import on first start
- May take 30-60 seconds after `./dev up`
- Check n8n logs: `./dev logs n8n`

### Lawyer Chat not working
- Ensure NEXTAUTH_SECRET is set in .env
- Check logs: `./dev logs lawyer-chat`
- Try restart: `./dev restart lawyer-chat`

## What's Running?

| Service | Purpose | Required |
|---------|---------|----------|
| web | NGINX proxy | Yes |
| db | PostgreSQL database | Yes |
| n8n | Workflow automation | Yes |
| redis | Session storage | Yes |
| lawyer-chat | Legal AI chat | Optional |
| court-processor | Document processing | Optional |
| ai-portal | AI services UI | Optional |

## Next Steps

Once running:
1. Access n8n at http://localhost:8080/n8n
2. Check workflows are imported (they auto-load)
3. Test the main app at http://localhost:8080
4. Try Lawyer Chat at http://localhost:8080/chat

For detailed documentation, see [README.md](README.md)

## Need Help?

- Run `./dev help` for all commands
- Check service logs: `./dev logs [service-name]`
- See full docs in `/docs` directory